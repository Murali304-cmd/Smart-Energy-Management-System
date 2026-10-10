import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import torch
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from models.solar_mlp import SolarMLPModel
from models.load_lstm import LoadLSTMModel
from models.price_xgboost import PriceXGBoostModel
from prediction.predictor import EnergyPredictorService

@pytest.fixture
def sample_weather_df():
    rows = []
    base_ts = pd.Timestamp('2026-09-10 00:00:00', tz='UTC')
    for i in range(50):
        ts = base_ts + pd.Timedelta(hours=i)
        hour = ts.hour
        temp = 28.0 + 5.0 * np.sin(np.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 24.0
        cloud = 20.0
        solar = max(0.0, 800.0 * np.sin(np.pi * (hour - 6) / 12) * (1 - 0.75 * (cloud / 100) ** 3)) if 6 <= hour <= 18 else 0.0
        rows.append({'timestamp': ts.isoformat(), 'temperature': round(temp, 2), 'humidity': 65.0, 'cloud_cover': cloud, 'wind_speed': 3.5, 'solar_irradiance_proxy': round(solar, 2), 'heat_index': round(temp + 2.0, 2), 'hour': hour, 'day': ts.day, 'month': ts.month, 'weekday': ts.weekday(), 'is_weekend': int(ts.weekday() >= 5), 'sin_hour': np.sin(2 * np.pi * hour / 24), 'cos_hour': np.cos(2 * np.pi * hour / 24)})
    return pd.DataFrame(rows)

@pytest.fixture
def sample_energy_df():
    rows = []
    base_ts = pd.Timestamp('2026-09-10 00:00:00', tz='UTC')
    for i in range(60):
        ts = base_ts + pd.Timedelta(minutes=i * 15)
        hour = ts.hour
        base_load = 1.2 + (1.5 if 7 <= hour <= 10 or 18 <= hour <= 22 else 0.3)
        rows.append({'timestamp': ts.isoformat(), 'meter_id': 'METER_TEST', 'energy_usage': round(base_load, 2), 'previous_energy_usage': round(base_load - 0.1, 2), 'lag_1': round(base_load - 0.1, 2), 'lag_2': round(base_load - 0.2, 2), 'lag_3': round(base_load - 0.15, 2), 'lag_4': round(base_load - 0.25, 2), 'rolling_mean_4': round(base_load - 0.1, 2), 'rolling_std_4': 0.08, 'hour': hour, 'day': ts.day, 'month': ts.month, 'weekday': ts.weekday(), 'is_weekend': int(ts.weekday() >= 5), 'sin_hour': np.sin(2 * np.pi * hour / 24), 'cos_hour': np.cos(2 * np.pi * hour / 24)})
    return pd.DataFrame(rows)

@pytest.fixture
def sample_tneb_df():
    rows = []
    base_ts = pd.Timestamp('2024-01-01', tz='UTC')
    for i in range(30):
        ts = base_ts + pd.Timedelta(days=i * 30)
        units = 250 + i % 5 * 50
        cost_per_unit = 4.7 if units <= 400 else 6.3
        bill = units * cost_per_unit
        rows.append({'original_record_id': f'REC_{i + 1}', 'consumer_number': f'CONS_{i % 3 + 1}', 'billing_date': ts.isoformat(), 'previous_reading': 1000 + i * 250, 'current_reading': 1000 + (i + 1) * 250, 'units_consumed': units, 'tariff_category': 'Domestic (<= 500 Units)', 'tariff_tier_code': 1, 'bill_amount': round(bill, 2), 'electricity_cost': round(bill, 2), 'effective_cost_per_unit': round(cost_per_unit, 2), 'prev_cycle_units': units - 10, 'consumption_trend': 10.0, 'month': ts.month, 'weekday': ts.weekday(), 'payment_status': 'Paid'})
    return pd.DataFrame(rows)

def test_solar_mlp_training_and_prediction(sample_weather_df, tmp_path):
    model = SolarMLPModel(epochs=15, batch_size=16)
    train_res = model.train(sample_weather_df)
    assert train_res['status'] == 'success'
    assert 'metrics' in train_res
    assert 'R2' in train_res['metrics']
    assert 'MAE' in train_res['metrics']
    test_input = sample_weather_df.iloc[[10]]
    pred = model.predict(test_input)
    assert len(pred) == 1
    assert pred[0] >= 0.0
    model.save(tmp_path)
    loaded_model = SolarMLPModel()
    loaded_model.load(tmp_path)
    pred_reloaded = loaded_model.predict(test_input)
    assert pred_reloaded[0] == pytest.approx(pred[0], abs=0.001)

def test_load_lstm_training_and_prediction(sample_energy_df, tmp_path):
    model = LoadLSTMModel(epochs=15, batch_size=16, sequence_length=12)
    train_res = model.train(sample_energy_df)
    assert train_res['status'] == 'success'
    assert 'metrics' in train_res
    assert 'MAE' in train_res['metrics']
    pred_kw = model.predict(sample_energy_df.iloc[-15:])
    assert isinstance(pred_kw, float)
    assert pred_kw > 0.0
    model.save(tmp_path)
    loaded_model = LoadLSTMModel(sequence_length=12)
    loaded_model.load(tmp_path)
    pred_reloaded = loaded_model.predict(sample_energy_df.iloc[-15:])
    assert pred_reloaded == pytest.approx(pred_kw, abs=0.01)

def test_price_xgboost_training_and_prediction(sample_tneb_df, tmp_path):
    model = PriceXGBoostModel(n_estimators=30)
    train_res = model.train(sample_tneb_df)
    assert train_res['status'] == 'success'
    assert 'metrics' in train_res
    assert 'R2' in train_res['metrics']
    test_input = sample_tneb_df.iloc[[5]]
    pred = model.predict(test_input)
    assert len(pred) == 1
    assert pred[0] > 0.0
    model.save(tmp_path)
    loaded_model = PriceXGBoostModel()
    loaded_model.load(tmp_path)
    pred_reloaded = loaded_model.predict(test_input)
    assert pred_reloaded[0] == pytest.approx(pred[0], abs=0.01)

def test_predictor_service_live_inference(sample_weather_df, sample_energy_df, sample_tneb_df):
    service = EnergyPredictorService()
    solar_val = service.predict_solar(sample_weather_df.iloc[10].to_dict())
    assert isinstance(solar_val, float)
    assert solar_val >= 0.0
    load_val = service.predict_energy_load(sample_energy_df.iloc[-15:])
    assert isinstance(load_val, float)
    assert load_val > 0.0
    price_val = service.predict_price(sample_tneb_df.iloc[2].to_dict())
    assert isinstance(price_val, float)
    assert price_val > 0.0
    all_preds = service.predict_all(weather_input=sample_weather_df.iloc[10].to_dict(), recent_energy_sequence=sample_energy_df.iloc[-15:], tneb_input=sample_tneb_df.iloc[2].to_dict())
    assert 'solar_prediction_kw' in all_preds
    assert 'load_prediction_kw' in all_preds
    assert 'price_prediction' in all_preds

def test_missing_feature_error_handling(sample_weather_df):
    model = SolarMLPModel()
    df_missing = sample_weather_df.drop(columns=['temperature'])
    valid, msg = model.validate_data(df_missing)
    assert 'temperature' not in model.feature_columns
