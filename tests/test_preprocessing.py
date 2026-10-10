import os
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pytest
import pandas as pd
import numpy as np
from preprocessing.data_loader import DataLoader
from preprocessing.data_cleaner import DataCleaner
from preprocessing.feature_engineering import FeatureEngineering
from preprocessing.data_quality import DataQualityReporter
from preprocessing.preprocessing_pipeline import PreprocessingPipeline

@pytest.fixture
def sample_weather_df():
    return pd.DataFrame({'timestamp': ['2026-09-10T06:00:00Z', '2026-09-10T06:00:00Z', '2026-09-10T07:00:00Z', '2026-09-10T08:00:00Z', '2026-09-10T09:00:00Z'], 'temperature': [28.5, 28.5, 30.0, 150.0, 32.5], 'humidity': [75.0, 75.0, 68.0, 65.0, -10.0], 'cloud_cover': [20.0, 20.0, None, 50.0, 10.0], 'wind_speed': [3.5, 3.5, 4.0, 2.8, 3.1], 'weather_condition': ['Clear', 'Clear', 'Clouds', 'Clouds', 'Clear']})

@pytest.fixture
def sample_energy_df():
    return pd.DataFrame({'timestamp': ['2026-09-10T06:00:00Z', '2026-09-10T06:15:00Z', '2026-09-10T06:15:00Z', '2026-09-10T06:30:00Z', '2026-09-10T06:45:00Z'], 'energy_usage': [1.2, 1.5, 1.5, -5.0, 1.8], 'unit': ['kW', 'kW', 'kW', 'kW', 'kW'], 'meter_id': ['METER01', 'METER01', 'METER01', 'METER01', 'METER01']})

@pytest.fixture
def sample_tneb_df():
    return pd.DataFrame({'original_record_id': ['TNEB_01', 'TNEB_02', 'TNEB_03'], 'consumer_number': ['CONS_001', 'CONS_001', 'CONS_002'], 'billing_date': ['2026-01-15', '2026-03-15', '2026-02-10'], 'previous_reading': [1000.0, 1250.0, 500.0], 'current_reading': [1250.0, 1550.0, 850.0], 'units_consumed': [250.0, 300.0, 350.0], 'tariff_category': ['Domestic (<= 500 Units)', 'Domestic (<= 500 Units)', 'Domestic (> 500 Units)'], 'bill_amount': [235.0, 470.0, 950.0], 'payment_status': ['Paid', 'Paid', 'Paid']})

def test_weather_cleaning_and_invalid_filtering(sample_weather_df):
    cleaner = DataCleaner()
    cleaned = cleaner.clean_weather_data(sample_weather_df)
    assert len(cleaned) < len(sample_weather_df)
    assert (cleaned['temperature'] <= 60.0).all()
    assert (cleaned['humidity'] >= 0.0).all()
    assert pd.api.types.is_datetime64_any_dtype(cleaned['timestamp'])

def test_energy_cleaning_and_negative_filtering(sample_energy_df):
    cleaner = DataCleaner()
    cleaned = cleaner.clean_energy_data(sample_energy_df)
    assert (cleaned['energy_usage'] >= 0.0).all()
    assert len(cleaned[cleaned['timestamp'] == '2026-09-10T06:15:00+00:00']) <= 1

def test_tneb_cleaning(sample_tneb_df):
    cleaner = DataCleaner()
    cleaned = cleaner.clean_tneb_data(sample_tneb_df)
    assert len(cleaned) == 3
    assert (cleaned['units_consumed'] >= 0).all()
    assert (cleaned['bill_amount'] >= 0).all()

def test_feature_engineering_time_and_lags(sample_energy_df):
    cleaner = DataCleaner()
    cleaned_energy = cleaner.clean_energy_data(sample_energy_df)
    fe = FeatureEngineering()
    energy_fe = fe.engineer_energy_features(cleaned_energy)
    assert 'hour' in energy_fe.columns
    assert 'sin_hour' in energy_fe.columns
    assert 'cos_hour' in energy_fe.columns
    assert 'lag_1' in energy_fe.columns
    assert 'lag_2' in energy_fe.columns
    assert 'rolling_mean_4' in energy_fe.columns

def test_tneb_cost_features(sample_tneb_df):
    fe = FeatureEngineering()
    tneb_fe = fe.engineer_tneb_features(sample_tneb_df)
    assert 'electricity_cost' in tneb_fe.columns
    assert 'effective_cost_per_unit' in tneb_fe.columns
    assert 'tariff_tier_code' in tneb_fe.columns
    assert tneb_fe.iloc[0]['effective_cost_per_unit'] == pytest.approx(0.94, abs=0.01)

def test_data_synchronization():
    cleaner = DataCleaner()
    fe = FeatureEngineering()
    ts_energy = pd.date_range('2026-09-10 06:00:00', periods=8, freq='15min', tz='UTC')
    energy_df = pd.DataFrame({'timestamp': ts_energy, 'energy_usage': [1.0, 1.2, 1.4, 1.3, 2.0, 2.1, 2.2, 2.0], 'meter_id': 'METER_01'})
    ts_weather = pd.date_range('2026-09-10 06:00:00', periods=2, freq='1h', tz='UTC')
    weather_df = pd.DataFrame({'timestamp': ts_weather, 'temperature': [28.0, 31.0], 'humidity': [70.0, 60.0], 'cloud_cover': [20.0, 40.0], 'wind_speed': [3.0, 4.0]})
    w_fe = fe.engineer_weather_features(weather_df)
    e_fe = fe.engineer_energy_features(energy_df)
    combined = fe.synchronize_datasets(e_fe, w_fe)
    assert len(combined) == 8
    assert (combined.iloc[0:4]['temperature'] == 28.0).all()
    assert (combined.iloc[4:8]['temperature'] == 31.0).all()

def test_end_to_end_pipeline():
    pipeline = PreprocessingPipeline()
    processed = pipeline.run(verbose=False)
    assert 'weather' in processed
    assert 'energy' in processed
    assert 'tneb' in processed
    assert 'combined' in processed
    assert (pipeline.output_dir / 'weather_processed.csv').exists()
    assert (pipeline.output_dir / 'energy_processed.csv').exists()
    assert (pipeline.output_dir / 'tneb_processed.csv').exists()
    assert (pipeline.output_dir / 'energy_management_processed.csv').exists()
    assert (pipeline.scalers_dir / 'weather_scaler.joblib').exists()
    assert (pipeline.scalers_dir / 'energy_scaler.joblib').exists()
    assert (pipeline.scalers_dir / 'tneb_scaler.joblib').exists()
    assert (pipeline.scalers_dir / 'combined_scaler.joblib').exists()

def test_no_electricity_price_api_in_codebase():
    assert not Path('api/electricity_price_api.py').exists(), 'electricity_price_api.py must not exist'
    import config.settings as s
    assert not hasattr(s, 'ENTSOE_SECURITY_TOKEN'), 'ENTSOE token should not exist in settings'
