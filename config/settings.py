import os
from pathlib import Path
from typing import Dict
BASE_DIR = Path(__file__).resolve().parent.parent

def load_env(env_path: Path=BASE_DIR / '.env') -> None:
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and (not line.startswith('#')) and ('=' in line):
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip().strip('\'"')
                    if key not in os.environ:
                        os.environ[key] = val
load_env()
DATABASE_PATH = Path(os.getenv('DATABASE_PATH', str(BASE_DIR / 'database' / 'smart_energy.db')))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BASE_DIR / DATABASE_PATH
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '').strip()
WEATHER_LAT = float(os.getenv('WEATHER_LAT', '13.0827'))
WEATHER_LON = float(os.getenv('WEATHER_LON', '80.2707'))
WEATHER_API_BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
SMART_METER_API_URL = os.getenv('SMART_METER_API_URL', '').strip()
SMART_METER_API_KEY = os.getenv('SMART_METER_API_KEY', '').strip()
SMART_METER_DEFAULT_ID = os.getenv('SMART_METER_DEFAULT_ID', 'METER_TNEB_001')
PROCESSED_DATA_DIR = BASE_DIR / 'data' / 'processed'
TRAINED_MODELS_DIR = BASE_DIR / 'trained_models'
SCALERS_DIR = BASE_DIR / 'trained_models' / 'scalers'
TNEB_DATASET_PATH = Path(os.getenv('TNEB_DATASET_PATH', str(BASE_DIR / 'data' / 'historical' / 'tneb_dataset.csv')))
if not TNEB_DATASET_PATH.is_absolute():
    TNEB_DATASET_PATH = BASE_DIR / TNEB_DATASET_PATH
ELECTRICITY_TARIFF_PATH = Path(os.getenv('ELECTRICITY_TARIFF_PATH', str(BASE_DIR / 'data' / 'historical' / 'electricity_price_tariff.csv')))
if not ELECTRICITY_TARIFF_PATH.is_absolute():
    ELECTRICITY_TARIFF_PATH = BASE_DIR / ELECTRICITY_TARIFF_PATH
DEFAULT_TNEB_COLUMN_MAPPING: Dict[str, str] = {'original_record_id': 'record_id,id,bill_id,sl_no,consumer_id', 'consumer_number': 'consumer_number,consumer_no,consumer_id,service_number,acc_no', 'billing_date': 'billing_date,bill_date,date,reading_date,bill_month_year', 'previous_reading': 'previous_reading,prev_reading,previous_kwh,prev_units,initial_reading', 'current_reading': 'current_reading,curr_reading,current_kwh,current_units,final_reading', 'units_consumed': 'units_consumed,units,consumption,kwh_consumed,consumed_units', 'tariff_category': 'tariff_category,tariff,category,consumer_category,type', 'bill_amount': 'bill_amount,amount,total_amount,bill_inr,amount_payable,net_amount', 'due_date': 'due_date,payment_due_date,last_date', 'payment_status': 'payment_status,status,paid_status,is_paid'}

def get_mapped_columns(available_columns: list) -> Dict[str, str]:
    resolved_mapping = {}
    normalized_headers = {col.strip().lower().replace(' ', '_'): col for col in available_columns}
    for internal_name, aliases in DEFAULT_TNEB_COLUMN_MAPPING.items():
        alias_list = [a.strip().lower().replace(' ', '_') for a in aliases.split(',')]
        alias_list.insert(0, internal_name.lower())
        for alias in alias_list:
            if alias in normalized_headers:
                resolved_mapping[internal_name] = normalized_headers[alias]
                break
    return resolved_mapping
BATTERY_CAPACITY_KWH = float(os.getenv('BATTERY_CAPACITY_KWH', '1000.0'))
BATTERY_MIN_SOC = float(os.getenv('BATTERY_MIN_SOC', '20.0'))
BATTERY_MAX_SOC = float(os.getenv('BATTERY_MAX_SOC', '100.0'))
BATTERY_DISCHARGE_EFFICIENCY = float(os.getenv('BATTERY_DISCHARGE_EFFICIENCY', '0.96'))
BATTERY_CHARGE_EFFICIENCY = float(os.getenv('BATTERY_CHARGE_EFFICIENCY', '0.96'))
BATTERY_MAX_DISCHARGE_KW = float(os.getenv('BATTERY_MAX_DISCHARGE_KW', '500.0'))
BATTERY_MAX_CHARGE_KW = float(os.getenv('BATTERY_MAX_CHARGE_KW', '500.0'))
BATTERY_MODEL_NAME = "Sungrow PowerTitan ST1000KWh Liquid-Cooled BESS"
BATTERY_MANUFACTURER = "Sungrow Power Supply Co."
BATTERY_PCS_RATING_KW = 500.0
BATTERY_CHEMISTRY = "LiFePO4 (LFP) 314Ah Prismatic"
BATTERY_CYCLE_LIFE = 8000
BATTERY_COOLING_TYPE = "Liquid Cooling (Glycol Closed-Loop)"
DESIRED_BACKUP_HOURS = float(os.getenv('DESIRED_BACKUP_HOURS', '10.0'))
AVERAGE_HOUSEHOLD_LOAD_KW = float(os.getenv('AVERAGE_HOUSEHOLD_LOAD_KW', '2.0'))
SOLAR_SYSTEM_CAPACITY_KW = float(os.getenv('SOLAR_SYSTEM_CAPACITY_KW', '5.0'))
SOLAR_INVERTER_API_URL = os.getenv('SOLAR_INVERTER_API_URL', '').strip()
SOLAR_INVERTER_API_KEY = os.getenv('SOLAR_INVERTER_API_KEY', '').strip()
# Real Battery API (Enode & Multi-Provider Settings)
BATTERY_MODE = os.getenv('BATTERY_MODE', 'demo').strip().lower()
ENODE_API_URL = os.getenv('ENODE_API_URL', 'https://enode-api.production.enode.io').strip().rstrip('/')
ENODE_CLIENT_ID = os.getenv('ENODE_CLIENT_ID', '').strip()
ENODE_CLIENT_SECRET = os.getenv('ENODE_CLIENT_SECRET', '').strip()
ENODE_BATTERY_ID = os.getenv('ENODE_BATTERY_ID', '').strip()
ENODE_USER_ID = os.getenv('ENODE_USER_ID', '').strip()
BATTERY_POLL_INTERVAL_SECONDS = int(os.getenv('BATTERY_POLL_INTERVAL_SECONDS', '15'))

SMAPPEE_CLIENT_ID = os.getenv('SMAPPEE_CLIENT_ID', '').strip()
SMAPPEE_CLIENT_SECRET = os.getenv('SMAPPEE_CLIENT_SECRET', '').strip()
SMAPPEE_API_URL = os.getenv('SMAPPEE_API_URL', 'https://api.smappee.net/v3').strip()
BATTERY_STATE_FILE = BASE_DIR / 'data' / 'battery_state.json'
DQN_LEARNING_RATE = float(os.getenv('DQN_LEARNING_RATE', '0.001'))
DQN_GAMMA = float(os.getenv('DQN_GAMMA', '0.95'))
DQN_EPSILON_START = float(os.getenv('DQN_EPSILON_START', '1.0'))
DQN_EPSILON_MIN = float(os.getenv('DQN_EPSILON_MIN', '0.05'))
DQN_EPSILON_DECAY = float(os.getenv('DQN_EPSILON_DECAY', '0.995'))
DQN_BATCH_SIZE = int(os.getenv('DQN_BATCH_SIZE', '64'))
DQN_MEMORY_SIZE = int(os.getenv('DQN_MEMORY_SIZE', '10000'))
DQN_TARGET_UPDATE_FREQ = int(os.getenv('DQN_TARGET_UPDATE_FREQ', '10'))
DQN_EPISODES = int(os.getenv('DQN_EPISODES', '300'))
DQN_MODEL_PATH = BASE_DIR / 'trained_models' / 'dqn_energy_recommender.pth'
DQN_META_PATH = BASE_DIR / 'trained_models' / 'dqn_metadata.json'

