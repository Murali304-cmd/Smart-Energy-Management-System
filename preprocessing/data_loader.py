import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from config.settings import DATABASE_PATH, DEFAULT_TNEB_COLUMN_MAPPING, get_mapped_columns
logger = logging.getLogger('SEMS.DataLoader')

class DataLoader:

    def __init__(self, db_path: Optional[Path]=None):
        self.db_path = Path(db_path or DATABASE_PATH)
        if not self.db_path.exists():
            logger.warning(f'Database path does not exist at init: {self.db_path}')

    def get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f'Database not found at {self.db_path}')
        return sqlite3.connect(str(self.db_path))

    def load_weather_data(self) -> pd.DataFrame:
        query = '\n        SELECT id, timestamp, temperature, humidity, cloud_cover, wind_speed,\n               weather_condition, latitude, longitude, data_type, source, created_at\n        FROM weather_data\n        ORDER BY timestamp ASC;\n        '
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
            logger.info(f'Loaded {len(df)} records from weather_data table.')
            return df
        except Exception as e:
            logger.error(f'Failed to load weather data: {e}')
            return pd.DataFrame(columns=['id', 'timestamp', 'temperature', 'humidity', 'cloud_cover', 'wind_speed', 'weather_condition', 'latitude', 'longitude', 'data_type', 'source', 'created_at'])

    def load_energy_data(self) -> pd.DataFrame:
        query = '\n        SELECT id, timestamp, energy_usage, unit, meter_id, data_type, source, created_at\n        FROM energy_data\n        ORDER BY timestamp ASC;\n        '
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
            logger.info(f'Loaded {len(df)} records from energy_data table.')
            return df
        except Exception as e:
            logger.error(f'Failed to load energy data: {e}')
            return pd.DataFrame(columns=['id', 'timestamp', 'energy_usage', 'unit', 'meter_id', 'data_type', 'source', 'created_at'])

    def load_tneb_data(self, custom_mapping: Optional[Dict[str, str]]=None) -> pd.DataFrame:
        query = '\n        SELECT *\n        FROM historical_tneb_data\n        ORDER BY billing_date ASC, id ASC;\n        '
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
            if df.empty:
                logger.warning('historical_tneb_data table is empty.')
                return df
            available_cols = df.columns.tolist()
            mapping = custom_mapping or get_mapped_columns(available_cols)
            logger.info(f'Loaded {len(df)} records from historical_tneb_data. Mapped columns: {list(mapping.keys())}')
            return df
        except Exception as e:
            logger.error(f'Failed to load historical TNEB data: {e}')
            return pd.DataFrame()

    def load_tariff_data(self) -> pd.DataFrame:
        query = '\n        SELECT id, category, slab_range, rate_per_unit_inr, tax_rate_percent, notes, data_type, source\n        FROM electricity_tariff_data\n        ORDER BY id ASC;\n        '
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
            logger.info(f'Loaded {len(df)} records from electricity_tariff_data table.')
            return df
        except Exception as e:
            logger.error(f'Failed to load tariff data: {e}')
            return pd.DataFrame(columns=['id', 'category', 'slab_range', 'rate_per_unit_inr', 'tax_rate_percent', 'notes', 'data_type', 'source'])

    def load_all_raw(self) -> Dict[str, pd.DataFrame]:
        return {'weather': self.load_weather_data(), 'energy': self.load_energy_data(), 'tneb': self.load_tneb_data(), 'tariffs': self.load_tariff_data()}
