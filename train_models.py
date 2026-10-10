import sys
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import pandas as pd
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from config.settings import PROCESSED_DATA_DIR, SCALERS_DIR
from models.solar_mlp import SolarMLPModel
from models.load_lstm import LoadLSTMModel
from models.price_xgboost import PriceXGBoostModel
TRAINED_MODELS_DIR = BASE_DIR / 'trained_models'
TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger('SEMS.TrainModels')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def train_all_models() -> Dict[str, Any]:
    print('========================================')
    print('ML MODEL TRAINING')
    print('========================================')
    weather_path = PROCESSED_DATA_DIR / 'weather_processed.csv'
    energy_path = PROCESSED_DATA_DIR / 'energy_processed.csv'
    tneb_path = PROCESSED_DATA_DIR / 'tneb_processed.csv'
    metadata = {'training_timestamp': datetime.now(timezone.utc).isoformat(), 'models': {}}
    performance_records = {}
    print('\n[1] Solar MLP')
    if not weather_path.exists():
        print('✗ Processed weather dataset not found.')
        solar_mlp = None
    else:
        df_weather = pd.read_csv(weather_path)
        print('✓ Dataset loaded')
        solar_mlp = SolarMLPModel(epochs=80, learning_rate=0.005)
        valid, msg = solar_mlp.validate_data(df_weather)
        if not valid:
            print(f'✗ {msg}')
        else:
            print('✓ Features selected')
            res_solar = solar_mlp.train(df_weather)
            if res_solar.get('status') == 'success':
                print('✓ Model trained')
                print('✓ Model evaluated')
                solar_mlp.save(TRAINED_MODELS_DIR)
                print('✓ Model saved')
                performance_records['Solar MLP'] = res_solar['metrics']
                metadata['models']['solar_mlp'] = {'target': res_solar['target'], 'features': res_solar['features'], 'metrics': res_solar['metrics']}
            else:
                print(f"✗ {res_solar.get('message')}")
    print('\n[2] Energy Load LSTM')
    if not energy_path.exists():
        print('✗ Processed energy dataset not found.')
        load_lstm = None
    else:
        df_energy = pd.read_csv(energy_path)
        print('✓ Dataset loaded')
        load_lstm = LoadLSTMModel(epochs=60, learning_rate=0.003)
        valid, msg = load_lstm.validate_data(df_energy)
        if not valid:
            print(f'✗ {msg}')
        else:
            print('✓ Sequences created')
            res_load = load_lstm.train(df_energy)
            if res_load.get('status') == 'success':
                print('✓ Model trained')
                print('✓ Model evaluated')
                load_lstm.save(TRAINED_MODELS_DIR)
                print('✓ Model saved')
                performance_records['Load LSTM'] = res_load['metrics']
                metadata['models']['load_lstm'] = {'target': res_load['target'], 'sequence_length': res_load['sequence_length'], 'features': res_load['features'], 'metrics': res_load['metrics']}
            else:
                print(f"✗ {res_load.get('message')}")
    print('\n[3] Electricity Price XGBoost')
    if not tneb_path.exists():
        print('✗ Processed TNEB historical dataset not found.')
        price_xgb = None
    else:
        df_tneb = pd.read_csv(tneb_path)
        print('✓ TNEB dataset loaded')
        price_xgb = PriceXGBoostModel(n_estimators=100, learning_rate=0.05)
        valid, msg = price_xgb.validate_data(df_tneb)
        if not valid:
            print(f'✗ {msg}')
        else:
            print('✓ Target identified')
            res_price = price_xgb.train(df_tneb)
            if res_price.get('status') == 'success':
                print('✓ Model trained')
                print('✓ Model evaluated')
                price_xgb.save(TRAINED_MODELS_DIR)
                print('✓ Model saved')
                performance_records['Price XGBoost'] = res_price['metrics']
                metadata['models']['price_xgboost'] = {'target': res_price['target'], 'features': res_price['features'], 'metrics': res_price['metrics']}
            else:
                print(f"✗ {res_price.get('message')}")
    meta_json_path = TRAINED_MODELS_DIR / 'metadata.json'
    with open(meta_json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print('\n=====================================')
    print('MODEL PERFORMANCE')
    print('=====================================')
    solar_m = performance_records.get('Solar MLP', {'MAE': 'N/A', 'RMSE': 'N/A', 'R2': 'N/A'})
    print('\nMLP Solar Prediction')
    print(f"MAE  : {solar_m.get('MAE')}")
    print(f"RMSE : {solar_m.get('RMSE')}")
    print(f"R²   : {solar_m.get('R2')}")
    load_m = performance_records.get('Load LSTM', {'MAE': 'N/A', 'RMSE': 'N/A', 'R2': 'N/A'})
    print('\nLSTM Load Prediction')
    print(f"MAE  : {load_m.get('MAE')}")
    print(f"RMSE : {load_m.get('RMSE')}")
    print(f"R²   : {load_m.get('R2')}")
    price_m = performance_records.get('Price XGBoost', {'MAE': 'N/A', 'RMSE': 'N/A', 'R2': 'N/A'})
    print('\nXGBoost Price Prediction')
    print(f"MAE  : {price_m.get('MAE')}")
    print(f"RMSE : {price_m.get('RMSE')}")
    print(f"R²   : {price_m.get('R2')}")
    print('=====================================')
    print('\n========================================')
    print('ML PREDICTION LAYER READY')
    print('========================================\n')
    return {'metadata': metadata, 'performance': performance_records}
if __name__ == '__main__':
    train_all_models()
