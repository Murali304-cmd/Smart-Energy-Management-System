import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from config.settings import TNEB_DATASET_PATH, ELECTRICITY_TARIFF_PATH, get_mapped_columns
from database.db_manager import DatabaseManager
from api.weather_api import get_current_weather
from api.smart_meter_api import get_current_energy_usage
logger = logging.getLogger('SEMS.DataCollector')

class DataCollectorService:

    def __init__(self, db_manager: Optional[DatabaseManager]=None):
        self.db = db_manager or DatabaseManager()

    def inspect_csv_headers(self, csv_path: Optional[Path]=None) -> List[str]:
        path = csv_path or TNEB_DATASET_PATH
        if not path.exists():
            raise FileNotFoundError(f'TNEB CSV dataset not found at {path}')
        with open(path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            return [h.strip() for h in headers]

    def import_tneb_dataset(self, csv_path: Optional[Path]=None, custom_mapping: Optional[Dict[str, str]]=None) -> Dict[str, Any]:
        path = csv_path or TNEB_DATASET_PATH
        if not path.exists():
            return {'status': 'error', 'message': f'Historical TNEB CSV not found at: {path}', 'records_stored': 0}
        try:
            with open(path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                raw_headers = reader.fieldnames or []
                mapping = custom_mapping if custom_mapping else get_mapped_columns(raw_headers)
                records = []
                for row in reader:
                    standardized_row: Dict[str, Any] = {}
                    for internal_field, csv_col in mapping.items():
                        standardized_row[internal_field] = row.get(csv_col)
                    records.append(standardized_row)
            result = self.db.insert_tneb_records(records)
            return {'status': 'success', 'total_rows': result['total_processed'], 'inserted': result['inserted'], 'skipped_duplicates': result['skipped'], 'message': f"Successfully processed {result['total_processed']} historical records."}
        except Exception as e:
            logger.error(f'Error importing historical TNEB dataset: {e}')
            return {'status': 'error', 'message': str(e), 'records_stored': 0}

    def import_electricity_tariff_dataset(self, csv_path: Optional[Path]=None) -> Dict[str, Any]:
        path = csv_path or ELECTRICITY_TARIFF_PATH
        if not path.exists():
            return {'status': 'error', 'message': f'Tariff dataset not found at: {path}', 'inserted': 0}
        try:
            with open(path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                records = list(reader)
            result = self.db.insert_tariff_records(records)
            return {'status': 'success', 'total_rows': result['total_processed'], 'inserted': result['inserted'], 'skipped_duplicates': result['skipped']}
        except Exception as e:
            logger.error(f'Error importing tariff dataset: {e}')
            return {'status': 'error', 'message': str(e), 'inserted': 0}

    def collect_weather(self, allow_demo: bool=True) -> Dict[str, Any]:
        weather_res = get_current_weather(allow_demo_fallback=allow_demo)
        if weather_res.get('status') == 'error':
            return weather_res
        success, msg = self.db.insert_weather(weather_res)
        weather_res['db_status'] = msg
        return {'status': 'success' if success else 'error', 'source': weather_res.get('source'), 'data_type': weather_res.get('data_type'), 'data': weather_res, 'message': msg}

    def collect_energy(self, allow_demo: bool=True) -> Dict[str, Any]:
        energy_res = get_current_energy_usage(allow_demo_fallback=allow_demo)
        if energy_res.get('status') == 'error':
            return energy_res
        success, msg = self.db.insert_energy(energy_res)
        energy_res['db_status'] = msg
        return {'status': 'success' if success else 'error', 'source': energy_res.get('source'), 'data_type': energy_res.get('data_type'), 'data': energy_res, 'message': msg}

    def collect_all(self) -> Dict[str, Any]:
        now_ts = datetime.now(timezone.utc).isoformat()
        tneb_status = self.import_tneb_dataset()
        tneb_summary = f"imported_{tneb_status.get('inserted')}" if tneb_status.get('inserted', 0) > 0 else 'already_imported'
        if tneb_status.get('status') == 'error':
            tneb_summary = f"error: {tneb_status.get('message')}"
        tariff_status = self.import_electricity_tariff_dataset()
        weather_status = self.collect_weather(allow_demo=True)
        w_summary = 'success' if weather_status.get('status') == 'success' else f"error: {weather_status.get('message')}"
        energy_status = self.collect_energy(allow_demo=True)
        e_summary = 'success' if energy_status.get('status') == 'success' else f"error: {energy_status.get('message')}"
        db_counts = self.db.get_counts()
        overall_ok = weather_status.get('status') == 'success' and energy_status.get('status') == 'success'
        return {'status': 'success' if overall_ok else 'partial', 'weather': w_summary, 'energy': e_summary, 'tneb': tneb_summary, 'tariff': tariff_status, 'timestamp': now_ts, 'db_counts': db_counts, 'latest_weather': weather_status.get('data'), 'latest_energy': energy_status.get('data')}
