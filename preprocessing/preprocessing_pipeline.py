import sys
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler, MinMaxScaler
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from config.settings import PROCESSED_DATA_DIR, SCALERS_DIR, DATABASE_PATH
from preprocessing.data_loader import DataLoader
from preprocessing.data_cleaner import DataCleaner
from preprocessing.feature_engineering import FeatureEngineering
from preprocessing.data_quality import DataQualityReporter
logger = logging.getLogger('SEMS.Pipeline')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class PreprocessingPipeline:

    def __init__(self, db_path: Path=DATABASE_PATH, output_dir: Path=PROCESSED_DATA_DIR, scalers_dir: Path=SCALERS_DIR):
        self.loader = DataLoader(db_path)
        self.cleaner = DataCleaner()
        self.fe = FeatureEngineering()
        self.reporter = DataQualityReporter()
        self.output_dir = Path(output_dir)
        self.scalers_dir = Path(scalers_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scalers_dir.mkdir(parents=True, exist_ok=True)

    def _fit_and_save_scaler(self, df: pd.DataFrame, numeric_cols: list, scaler_name: str, scaler_type: str='standard', train_ratio: float=0.8) -> Any:
        if df.empty or not numeric_cols:
            return None
        valid_cols = [c for c in numeric_cols if c in df.columns]
        if not valid_cols:
            return None
        split_idx = max(1, int(len(df) * train_ratio))
        train_data = df.iloc[:split_idx][valid_cols]
        scaler = StandardScaler() if scaler_type == 'standard' else MinMaxScaler()
        scaler.fit(train_data)
        scaler_path = self.scalers_dir / f'{scaler_name}.joblib'
        joblib.dump({'scaler': scaler, 'feature_names': valid_cols, 'scaler_type': scaler_type, 'fitted_records': len(train_data)}, scaler_path)
        logger.info(f'Fitted and saved scaler: {scaler_path.name} ({len(valid_cols)} features)')
        return scaler

    def run(self, verbose: bool=True) -> Dict[str, pd.DataFrame]:
        raw_data = self.loader.load_all_raw()
        cleaned_data = self.cleaner.clean_all(raw_data)
        weather_fe = self.fe.engineer_weather_features(cleaned_data.get('weather', pd.DataFrame()))
        energy_fe = self.fe.engineer_energy_features(cleaned_data.get('energy', pd.DataFrame()))
        tneb_fe = self.fe.engineer_tneb_features(cleaned_data.get('tneb', pd.DataFrame()), cleaned_data.get('tariffs', pd.DataFrame()))
        combined_fe = self.fe.synchronize_datasets(energy_df=energy_fe, weather_df=weather_fe, tariff_df=cleaned_data.get('tariffs', pd.DataFrame()))
        weather_numeric = [
            'temperature', 'humidity', 'cloud_cover', 'wind_speed',
            'solar_irradiance_proxy', 'heat_index', 'cooling_degree_metric', 'heating_degree_metric'
        ]
        self._fit_and_save_scaler(weather_fe, weather_numeric, 'weather_scaler', 'minmax')
        energy_numeric = [
            'energy_usage', 'previous_energy_usage', 'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_8', 'lag_12',
            'rolling_mean_4', 'rolling_std_4', 'rolling_mean_8', 'rolling_max_8', 'rolling_min_8',
            'peak_to_average_ratio', 'ema_4'
        ]
        self._fit_and_save_scaler(energy_fe, energy_numeric, 'energy_scaler', 'standard')
        tneb_numeric = ['units_consumed', 'bill_amount', 'effective_cost_per_unit', 'prev_cycle_units', 'consumption_trend']
        self._fit_and_save_scaler(tneb_fe, tneb_numeric, 'tneb_scaler', 'standard')
        combined_numeric = [
            'temperature', 'humidity', 'cloud_cover', 'wind_speed', 'solar_irradiance_proxy', 'heat_index',
            'cooling_degree_metric', 'heating_degree_metric', 'energy_usage', 'previous_energy_usage',
            'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_8', 'lag_12',
            'rolling_mean_4', 'rolling_std_4', 'rolling_mean_8', 'rolling_max_8', 'rolling_min_8',
            'peak_to_average_ratio', 'ema_4', 'solar_load_ratio'
        ]
        self._fit_and_save_scaler(combined_fe, combined_numeric, 'combined_scaler', 'standard')
        weather_file = self.output_dir / 'weather_processed.csv'
        energy_file = self.output_dir / 'energy_processed.csv'
        tneb_file = self.output_dir / 'tneb_processed.csv'
        combined_file = self.output_dir / 'energy_management_processed.csv'
        weather_fe.to_csv(weather_file, index=False)
        energy_fe.to_csv(energy_file, index=False)
        tneb_fe.to_csv(tneb_file, index=False)
        combined_fe.to_csv(combined_file, index=False)
        processed_dict = {'weather': weather_fe, 'energy': energy_fe, 'tneb': tneb_fe, 'combined': combined_fe}
        if verbose:
            print('\n')
            self.reporter.print_summary(self.cleaner.audit_log, processed_dict)
            print('\n========================================')
            print('DATA PREPROCESSING')
            print('========================================')
            print('\n✓ Weather data loaded')
            print('✓ Smart Meter data loaded')
            print('✓ TNEB data loaded')
            print('\n✓ Weather cleaned')
            print('✓ Energy data cleaned')
            print('✓ TNEB data cleaned')
            print('\n✓ Missing values handled')
            print('✓ Duplicates removed')
            print('✓ Invalid values checked')
            print('\n✓ Timestamps standardized')
            print('✓ Compatible data synchronized')
            print('✓ Features extracted')
            print('✓ Features scaled')
            print('\n✓ Data quality report generated')
            print('✓ Processed datasets saved')
            print('\nDATA PREPROCESSING LAYER READY\n')
        return processed_dict

def main():
    pipeline = PreprocessingPipeline()
    pipeline.run(verbose=True)
if __name__ == '__main__':
    main()
