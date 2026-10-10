import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests
from config.settings import SMART_METER_API_URL, SMART_METER_API_KEY, SMART_METER_DEFAULT_ID
logger = logging.getLogger('SEMS.SmartMeterAPI')

def get_current_energy_usage(api_url: Optional[str]=None, api_key: Optional[str]=None, meter_id: Optional[str]=None, allow_demo_fallback: bool=True) -> Dict[str, Any]:
    target_url = (api_url if api_url is not None else SMART_METER_API_URL).strip()
    target_key = (api_key if api_key is not None else SMART_METER_API_KEY).strip()
    target_meter_id = (meter_id if meter_id is not None else SMART_METER_DEFAULT_ID).strip()
    if not target_url:
        if allow_demo_fallback:
            return get_mock_energy_usage(target_meter_id)
        return {'status': 'error', 'source': 'SmartMeter', 'message': 'Smart Meter API URL not configured'}
    headers = {}
    if target_key:
        headers['Authorization'] = f'Bearer {target_key}'
        headers['X-API-Key'] = target_key
    params = {'meter_id': target_meter_id}
    try:
        response = requests.get(target_url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            ts_raw = data.get('timestamp') or datetime.now(timezone.utc).isoformat()
            usage = float(data.get('energy_usage', data.get('consumption', data.get('kwh', 0.0))))
            unit = str(data.get('unit', 'kW'))
            res_meter_id = str(data.get('meter_id', target_meter_id))
            household_id = data.get('household_id')
            result = {'status': 'success', 'timestamp': ts_raw, 'energy_usage': usage, 'unit': unit, 'meter_id': res_meter_id, 'data_type': 'live', 'source': 'SmartMeter'}
            if household_id:
                result['household_id'] = str(household_id)
            return result
        else:
            msg = f'Smart Meter API returned HTTP {response.status_code}'
            logger.warning(msg)
            if allow_demo_fallback:
                logger.info('Falling back to demo Smart Meter provider due to API unavailability.')
                return get_mock_energy_usage(target_meter_id)
            return {'status': 'error', 'source': 'SmartMeter', 'message': msg}
    except requests.exceptions.RequestException as e:
        logger.error(f'Network error contacting Smart Meter API: {e}')
        if allow_demo_fallback:
            logger.info('Falling back to demo Smart Meter provider due to connection error.')
            return get_mock_energy_usage(target_meter_id)
        return {'status': 'error', 'source': 'SmartMeter', 'message': 'Smart Meter API unavailable: Network error'}
    except Exception as e:
        logger.error(f'Unexpected error parsing smart meter data: {e}')
        return {'status': 'error', 'source': 'SmartMeter', 'message': f'Smart Meter processing error: {str(e)}'}

def get_mock_energy_usage(meter_id: str='METER_TNEB_001', household_id: str='HH_CH_101') -> Dict[str, Any]:
    simulated_load = round(random.uniform(1.2, 3.8), 2)
    return {'status': 'success', 'timestamp': datetime.now(timezone.utc).isoformat(), 'energy_usage': simulated_load, 'unit': 'kW', 'meter_id': meter_id, 'household_id': household_id, 'data_type': 'demo', 'source': 'SmartMeterDemo'}
