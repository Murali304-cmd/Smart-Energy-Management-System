import logging
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
logger = logging.getLogger('SEMS.DataCleaner')

class DataCleaner:

    def __init__(self):
        self.audit_log: Dict[str, Dict[str, Any]] = {}

    def _standardize_timestamps(self, df: pd.DataFrame, time_col: str) -> pd.DataFrame:
        if time_col not in df.columns or df.empty:
            return df
        df = df.copy()
        df[time_col] = pd.to_datetime(df[time_col], utc=True, errors='coerce')
        df = df.dropna(subset=[time_col])
        df = df.sort_values(by=time_col).reset_index(drop=True)
        return df

    def clean_weather_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        audit = {'source': 'OpenWeatherMap', 'initial_records': len(raw_df), 'duplicates_removed': 0, 'missing_before': 0, 'missing_after': 0, 'missing_method': 'forward_fill_then_backward_fill', 'invalid_removed': 0, 'final_records': 0}
        if raw_df.empty:
            self.audit_log['weather'] = audit
            return raw_df
        df = raw_df.copy()
        audit['missing_before'] = int(df.isna().sum().sum())
        df = self._standardize_timestamps(df, 'timestamp')
        dup_mask = df.duplicated(subset=['timestamp'], keep='last')
        audit['duplicates_removed'] = int(dup_mask.sum())
        df = df[~dup_mask].copy()
        numeric_cols = ['temperature', 'humidity', 'cloud_cover', 'wind_speed']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        initial_len = len(df)
        valid_mask = pd.Series(True, index=df.index)
        if 'temperature' in df.columns:
            valid_mask &= (df['temperature'] >= -10.0) & (df['temperature'] <= 60.0)
        if 'humidity' in df.columns:
            valid_mask &= (df['humidity'] >= 0.0) & (df['humidity'] <= 100.0)
        if 'cloud_cover' in df.columns:
            valid_mask &= df['cloud_cover'].isna() | (df['cloud_cover'] >= 0.0) & (df['cloud_cover'] <= 100.0)
        if 'wind_speed' in df.columns:
            valid_mask &= df['wind_speed'].isna() | (df['wind_speed'] >= 0.0)
        df = df[valid_mask].copy()
        audit['invalid_removed'] = initial_len - len(df)
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].ffill(limit=3).bfill(limit=1)
        if 'weather_condition' in df.columns:
            df['weather_condition'] = df['weather_condition'].fillna('Unknown')
        audit['missing_after'] = int(df[numeric_cols].isna().sum().sum()) if all((c in df.columns for c in numeric_cols)) else 0
        audit['final_records'] = len(df)
        self.audit_log['weather'] = audit
        logger.info(f"Weather cleaned: {audit['initial_records']} -> {audit['final_records']} records (Duplicates: {audit['duplicates_removed']}, Invalid: {audit['invalid_removed']})")
        return df.reset_index(drop=True)

    def clean_energy_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        audit = {'source': 'SmartMeter', 'initial_records': len(raw_df), 'duplicates_removed': 0, 'missing_before': 0, 'missing_after': 0, 'missing_method': 'time_interpolation_and_ffill', 'invalid_removed': 0, 'final_records': 0}
        if raw_df.empty:
            self.audit_log['energy'] = audit
            return raw_df
        df = raw_df.copy()
        audit['missing_before'] = int(df.isna().sum().sum())
        df = self._standardize_timestamps(df, 'timestamp')
        subset_keys = ['timestamp', 'meter_id'] if 'meter_id' in df.columns else ['timestamp']
        dup_mask = df.duplicated(subset=subset_keys, keep='last')
        audit['duplicates_removed'] = int(dup_mask.sum())
        df = df[~dup_mask].copy()
        if 'energy_usage' in df.columns:
            df['energy_usage'] = pd.to_numeric(df['energy_usage'], errors='coerce')
        if 'unit' in df.columns:
            df['unit'] = df['unit'].astype(str).str.strip()
            watts_mask = df['unit'].str.lower() == 'w'
            if watts_mask.any():
                df.loc[watts_mask, 'energy_usage'] = df.loc[watts_mask, 'energy_usage'] / 1000.0
                df.loc[watts_mask, 'unit'] = 'kW'
        initial_len = len(df)
        valid_mask = (df['energy_usage'] >= 0.0) & (df['energy_usage'] <= 150.0)
        df = df[valid_mask].copy()
        audit['invalid_removed'] = initial_len - len(df)
        df['energy_usage'] = df['energy_usage'].interpolate(method='linear', limit=2).ffill().bfill()
        audit['missing_after'] = int(df['energy_usage'].isna().sum())
        audit['final_records'] = len(df)
        self.audit_log['energy'] = audit
        logger.info(f"Energy data cleaned: {audit['initial_records']} -> {audit['final_records']} records (Duplicates: {audit['duplicates_removed']}, Invalid: {audit['invalid_removed']})")
        return df.reset_index(drop=True)

    def clean_tneb_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        audit = {'source': 'TNEB Kaggle Historical', 'initial_records': len(raw_df), 'duplicates_removed': 0, 'missing_before': 0, 'missing_after': 0, 'missing_method': 'drop_unrecoverable_billing_records', 'invalid_removed': 0, 'final_records': 0}
        if raw_df.empty:
            self.audit_log['tneb'] = audit
            return raw_df
        df = raw_df.copy()
        audit['missing_before'] = int(df.isna().sum().sum())
        date_col = 'billing_date' if 'billing_date' in df.columns else 'date' if 'date' in df.columns else None
        if date_col:
            df = self._standardize_timestamps(df, date_col)
        dup_subset = ['consumer_number', date_col] if 'consumer_number' in df.columns and date_col else ['original_record_id'] if 'original_record_id' in df.columns else [date_col] if date_col else None
        if dup_subset:
            dup_mask = df.duplicated(subset=dup_subset, keep='last')
            audit['duplicates_removed'] = int(dup_mask.sum())
            df = df[~dup_mask].copy()
        for col in ['units_consumed', 'bill_amount', 'previous_reading', 'current_reading']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        initial_len = len(df)
        valid_mask = pd.Series(True, index=df.index)
        if 'units_consumed' in df.columns:
            valid_mask &= (df['units_consumed'] >= 0.0) & (df['units_consumed'] <= 50000.0)
        if 'bill_amount' in df.columns:
            valid_mask &= df['bill_amount'] >= 0.0
        if 'previous_reading' in df.columns and 'current_reading' in df.columns:
            readings_valid = df['previous_reading'].isna() | df['current_reading'].isna() | (df['current_reading'] >= df['previous_reading'])
            valid_mask &= readings_valid
        df = df[valid_mask].copy()
        audit['invalid_removed'] = initial_len - len(df)
        essential_cols = [c for c in ['units_consumed', 'bill_amount'] if c in df.columns]
        if essential_cols:
            df = df.dropna(subset=essential_cols)
        audit['missing_after'] = int(df[essential_cols].isna().sum().sum()) if essential_cols else 0
        audit['final_records'] = len(df)
        self.audit_log['tneb'] = audit
        logger.info(f"TNEB data cleaned: {audit['initial_records']} -> {audit['final_records']} records (Duplicates: {audit['duplicates_removed']}, Invalid: {audit['invalid_removed']})")
        return df.reset_index(drop=True)

    def clean_all(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        cleaned = {}
        if 'weather' in raw_data:
            cleaned['weather'] = self.clean_weather_data(raw_data['weather'])
        if 'energy' in raw_data:
            cleaned['energy'] = self.clean_energy_data(raw_data['energy'])
        if 'tneb' in raw_data:
            cleaned['tneb'] = self.clean_tneb_data(raw_data['tneb'])
        if 'tariffs' in raw_data:
            cleaned['tariffs'] = raw_data['tariffs'].copy()
        return cleaned
