import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import pandas as pd
import numpy as np
from config.settings import BASE_DIR
from models.solar_mlp import SolarMLPModel
from models.load_lstm import LoadLSTMModel
from models.price_xgboost import PriceXGBoostModel
from preprocessing.feature_engineering import FeatureEngineering
logger = logging.getLogger('SEMS.Predictor')
TRAINED_MODELS_DIR = BASE_DIR / 'trained_models'

class EnergyPredictorService:

    def __init__(self, models_dir: Path=TRAINED_MODELS_DIR):
        self.models_dir = Path(models_dir)
        self.fe = FeatureEngineering()
        self.solar_model: Optional[SolarMLPModel] = None
        self.load_model: Optional[LoadLSTMModel] = None
        self.price_model: Optional[PriceXGBoostModel] = None
        self._load_available_models()

    def _load_available_models(self):
        try:
            solar = SolarMLPModel()
            solar.load(self.models_dir)
            self.solar_model = solar
            logger.info('Solar MLP model successfully loaded into predictor service.')
        except Exception as e:
            logger.warning(f'Solar MLP model not loaded: {e}')
        try:
            load = LoadLSTMModel()
            load.load(self.models_dir)
            self.load_model = load
            logger.info('Load LSTM model successfully loaded into predictor service.')
        except Exception as e:
            logger.warning(f'Load LSTM model not loaded: {e}')
        try:
            price = PriceXGBoostModel()
            price.load(self.models_dir)
            self.price_model = price
            logger.info('Price XGBoost model successfully loaded into predictor service.')
        except Exception as e:
            logger.warning(f'Price XGBoost model not loaded: {e}')

    def predict_solar(self, weather_input: Union[pd.DataFrame, Dict[str, Any]]) -> float:
        if self.solar_model is None or not self.solar_model.is_trained:
            raise RuntimeError("Solar MLP model is missing or not trained. Run 'python train_models.py' first.")
        if isinstance(weather_input, dict):
            df = pd.DataFrame([weather_input])
        else:
            df = weather_input.copy()
        if 'timestamp' in df.columns:
            df = self.fe.add_time_features(df, 'timestamp')
        elif 'time' in df.columns:
            df = self.fe.add_time_features(df, 'time')
        if 'hour' not in df.columns:
            df['hour'] = 12
        if 'day' not in df.columns:
            df['day'] = 15
        if 'month' not in df.columns:
            df['month'] = 9
        if 'weekday' not in df.columns:
            df['weekday'] = 3
        if 'is_weekend' not in df.columns:
            df['is_weekend'] = (df['weekday'] >= 5).astype(int)
        if 'sin_hour' not in df.columns:
            df['sin_hour'] = np.sin(2.0 * np.pi * df['hour'] / 24.0)
        if 'cos_hour' not in df.columns:
            df['cos_hour'] = np.cos(2.0 * np.pi * df['hour'] / 24.0)
        if 'sin_month' not in df.columns:
            df['sin_month'] = np.sin(2.0 * np.pi * (df['month'] - 1) / 12.0)
        if 'cos_month' not in df.columns:
            df['cos_month'] = np.cos(2.0 * np.pi * (df['month'] - 1) / 12.0)
        if 'temperature' not in df.columns:
            df['temperature'] = 30.0
        if 'humidity' not in df.columns:
            df['humidity'] = 65.0
        if 'cloud_cover' not in df.columns:
            df['cloud_cover'] = 20.0
        if 'wind_speed' not in df.columns:
            df['wind_speed'] = 3.5
        if 'heat_index' not in df.columns:
            t = pd.to_numeric(df['temperature'], errors='coerce').fillna(30.0)
            rh = pd.to_numeric(df['humidity'], errors='coerce').fillna(60.0)
            df['heat_index'] = np.round(0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094), 2)
        if 'cooling_degree_metric' not in df.columns:
            t = pd.to_numeric(df['temperature'], errors='coerce').fillna(30.0)
            df['cooling_degree_metric'] = np.maximum(0.0, t - 24.0).round(2)
        if 'heating_degree_metric' not in df.columns:
            t = pd.to_numeric(df['temperature'], errors='coerce').fillna(30.0)
            df['heating_degree_metric'] = np.maximum(0.0, 18.0 - t).round(2)
        hour_val = int(df['hour'].iloc[0])
        if hour_val < 6 or hour_val > 18:
            return 0.0
        preds = self.solar_model.predict(df)
        val = float(preds[0]) if len(preds) > 0 else 0.0
        return round(val, 2)

    def predict_energy_load(self, recent_sequence: Union[pd.DataFrame, List[Dict[str, Any]]]) -> float:
        if self.load_model is None or not self.load_model.is_trained:
            raise RuntimeError("Load LSTM model is missing or not trained. Run 'python train_models.py' first.")
        if isinstance(recent_sequence, list):
            df = pd.DataFrame(recent_sequence)
        else:
            df = recent_sequence.copy()
        if df.empty:
            return 2.2
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(by='timestamp').reset_index(drop=True)
        if 'energy_usage' not in df.columns:
            if 'load' in df.columns:
                df['energy_usage'] = df['load']
            else:
                df['energy_usage'] = 2.2
        df = self.fe.engineer_energy_features(df)
        seq_len = getattr(self.load_model, 'sequence_length', 12)
        if len(df) < seq_len:
            pad_needed = seq_len - len(df)
            first_row = df.iloc[0:1]
            pad_df = pd.concat([first_row] * pad_needed, ignore_index=True)
            df = pd.concat([pad_df, df], ignore_index=True)
        val = self.load_model.predict(df)
        return round(val, 2)

    def predict_price(self, tneb_input: Union[pd.DataFrame, Dict[str, Any]]) -> float:
        if self.price_model is None or not self.price_model.is_trained:
            raise RuntimeError("Electricity Price XGBoost model is missing or not trained. Run 'python train_models.py' first.")
        if isinstance(tneb_input, dict):
            df = pd.DataFrame([tneb_input])
        else:
            df = tneb_input.copy()
        defaults = {'units_consumed': 350.0, 'previous_reading': 1200.0, 'current_reading': 1550.0, 'tariff_tier_code': 1, 'prev_cycle_units': 330.0, 'consumption_trend': 20.0, 'month': 9, 'weekday': 3}
        for col, val in defaults.items():
            if col not in df.columns:
                df[col] = val
        preds = self.price_model.predict(df)
        val = float(preds[0]) if len(preds) > 0 else 0.0
        return round(val, 2)

    def predict_all(self, weather_input: Optional[Union[pd.DataFrame, Dict[str, Any]]]=None, recent_energy_sequence: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]]=None, tneb_input: Optional[Union[pd.DataFrame, Dict[str, Any]]]=None) -> Dict[str, Any]:
        results = {}
        if weather_input is not None:
            try:
                results['solar_prediction_kw'] = self.predict_solar(weather_input)
            except Exception as e:
                logger.error(f'Solar prediction error: {e}')
                results['solar_prediction_kw'] = None
        if recent_energy_sequence is not None:
            try:
                results['load_prediction_kw'] = self.predict_energy_load(recent_energy_sequence)
            except Exception as e:
                logger.error(f'Energy load prediction error: {e}')
                results['load_prediction_kw'] = None
        if tneb_input is not None:
            try:
                results['price_prediction'] = self.predict_price(tneb_input)
            except Exception as e:
                logger.error(f'Electricity price prediction error: {e}')
                results['price_prediction'] = None
        return results
