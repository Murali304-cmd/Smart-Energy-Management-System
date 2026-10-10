import logging
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger("SEMS.FeatureEngineering")

class FeatureEngineering:

    def __init__(self):
        pass

    def add_time_features(self, df: pd.DataFrame, time_col: str = "timestamp") -> pd.DataFrame:
        if df.empty or time_col not in df.columns:
            return df
        df = df.copy()
        ts = pd.to_datetime(df[time_col], utc=True)
        df["hour"] = ts.dt.hour
        df["day"] = ts.dt.day
        df["month"] = ts.dt.month
        df["weekday"] = ts.dt.weekday
        df["is_weekend"] = (df["weekday"] >= 5).astype(int)
        df["sin_hour"] = np.sin(2.0 * np.pi * df["hour"] / 24.0)
        df["cos_hour"] = np.cos(2.0 * np.pi * df["hour"] / 24.0)
        df["sin_month"] = np.sin(2.0 * np.pi * (df["month"] - 1) / 12.0)
        df["cos_month"] = np.cos(2.0 * np.pi * (df["month"] - 1) / 12.0)
        return df

    def engineer_weather_features(self, weather_df: pd.DataFrame) -> pd.DataFrame:
        if weather_df.empty:
            return weather_df
        df = weather_df.copy()
        df = self.add_time_features(df, "timestamp")
        hours_rad = (df["hour"] - 6.0) * np.pi / 12.0
        daylight_factor = np.maximum(0.0, np.sin(hours_rad))
        daylight_factor = np.where((df["hour"] >= 6) & (df["hour"] <= 18), daylight_factor, 0.0)
        cloud_ratio = df["cloud_cover"].fillna(20.0) / 100.0
        attenuation = np.maximum(0.1, 1.0 - 0.75 * (cloud_ratio ** 3))
        df["solar_irradiance_proxy"] = np.round(1000.0 * daylight_factor * attenuation, 2)
        t = df["temperature"]
        rh = df["humidity"]
        df["heat_index"] = np.round(0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094), 2)
        
        # Cooling / Heating degree indices (Baseline 24.0C and 18.0C)
        df["cooling_degree_metric"] = np.maximum(0.0, t - 24.0).round(2)
        df["heating_degree_metric"] = np.maximum(0.0, 18.0 - t).round(2)

        selected_columns = [
            "timestamp", "temperature", "humidity", "cloud_cover", "wind_speed",
            "solar_irradiance_proxy", "heat_index", "cooling_degree_metric", "heating_degree_metric",
            "hour", "day", "month", "weekday", "is_weekend", "sin_hour", "cos_hour"
        ]
        available_cols = [c for c in selected_columns if c in df.columns]
        return df[available_cols].reset_index(drop=True)

    def engineer_energy_features(self, energy_df: pd.DataFrame) -> pd.DataFrame:
        if energy_df.empty:
            return energy_df
        df = energy_df.copy()
        df = df.sort_values(by="timestamp").reset_index(drop=True)
        df = self.add_time_features(df, "timestamp")
        
        # Primary lag features
        df["previous_energy_usage"] = df["energy_usage"].shift(1)
        df["lag_1"] = df["energy_usage"].shift(1)
        df["lag_2"] = df["energy_usage"].shift(2)
        df["lag_3"] = df["energy_usage"].shift(3)
        df["lag_4"] = df["energy_usage"].shift(4)
        df["lag_8"] = df["energy_usage"].shift(8)
        df["lag_12"] = df["energy_usage"].shift(12)
        
        # Rolling window stats
        past_series = df["energy_usage"].shift(1)
        df["rolling_mean_4"] = np.round(past_series.rolling(window=4, min_periods=1).mean(), 3)
        df["rolling_std_4"] = np.round(past_series.rolling(window=4, min_periods=1).std().fillna(0.0), 3)
        df["rolling_mean_8"] = np.round(past_series.rolling(window=8, min_periods=1).mean(), 3)
        df["rolling_max_8"] = np.round(past_series.rolling(window=8, min_periods=1).max(), 3)
        df["rolling_min_8"] = np.round(past_series.rolling(window=8, min_periods=1).min(), 3)
        
        # Peak-to-Average Ratio (PAR) and Exponential Moving Average
        df["peak_to_average_ratio"] = np.round(df["rolling_max_8"] / (df["rolling_mean_8"] + 1e-5), 3)
        df["ema_4"] = np.round(past_series.ewm(span=4, min_periods=1).mean(), 3)

        lag_cols = [
            "previous_energy_usage", "lag_1", "lag_2", "lag_3", "lag_4", "lag_8", "lag_12",
            "rolling_mean_4", "rolling_std_4", "rolling_mean_8", "rolling_max_8", "rolling_min_8",
            "peak_to_average_ratio", "ema_4"
        ]
        df[lag_cols] = df[lag_cols].bfill().ffill()

        selected_columns = [
            "timestamp", "meter_id", "energy_usage", "unit",
            "previous_energy_usage", "lag_1", "lag_2", "lag_3", "lag_4", "lag_8", "lag_12",
            "rolling_mean_4", "rolling_std_4", "rolling_mean_8", "rolling_max_8", "rolling_min_8",
            "peak_to_average_ratio", "ema_4",
            "hour", "day", "month", "weekday", "is_weekend", "sin_hour", "cos_hour"
        ]
        available_cols = [c for c in selected_columns if c in df.columns]
        return df[available_cols].reset_index(drop=True)

    def engineer_tneb_features(self, tneb_df: pd.DataFrame, tariff_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if tneb_df.empty:
            return tneb_df
        df = tneb_df.copy()
        date_col = "billing_date" if "billing_date" in df.columns else "date" if "date" in df.columns else None
        if date_col:
            df = df.sort_values(by=date_col).reset_index(drop=True)
            df = self.add_time_features(df, date_col)
        if "bill_amount" in df.columns:
            df["electricity_cost"] = df["bill_amount"].astype(float)
        if "units_consumed" in df.columns and "bill_amount" in df.columns:
            valid_units = df["units_consumed"] > 0
            df["effective_cost_per_unit"] = 0.0
            df.loc[valid_units, "effective_cost_per_unit"] = np.round(
                df.loc[valid_units, "bill_amount"] / df.loc[valid_units, "units_consumed"], 2
            )
        if "tariff_category" in df.columns:
            cat_map = {
                "Domestic (<= 500 Units)": 1,
                "Domestic (> 500 Units)": 2,
                "Commercial (Low Cons.)": 3,
                "Commercial (High Cons.)": 4,
                "Industries & IT Services": 5
            }
            df["tariff_tier_code"] = df["tariff_category"].map(lambda x: cat_map.get(str(x).strip(), 0))
        if "consumer_number" in df.columns and "units_consumed" in df.columns:
            df["prev_cycle_units"] = df.groupby("consumer_number")["units_consumed"].shift(1).bfill()
            df["consumption_trend"] = np.round(df["units_consumed"] - df["prev_cycle_units"], 2)
        selected_columns = [
            "original_record_id", "consumer_number", "billing_date", "previous_reading",
            "current_reading", "units_consumed", "tariff_category", "tariff_tier_code",
            "bill_amount", "electricity_cost", "effective_cost_per_unit", "prev_cycle_units",
            "consumption_trend", "month", "weekday", "payment_status"
        ]
        available_cols = [c for c in selected_columns if c in df.columns]
        return df[available_cols].reset_index(drop=True)

    def synchronize_datasets(self, energy_df: pd.DataFrame, weather_df: pd.DataFrame, tariff_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if energy_df.empty:
            logger.warning("Energy dataset is empty, cannot synchronize.")
            return pd.DataFrame()
        e_df = energy_df.copy()
        e_df["timestamp"] = pd.to_datetime(e_df["timestamp"], utc=True)
        e_df = e_df.sort_values(by="timestamp").reset_index(drop=True)
        if not weather_df.empty:
            w_df = weather_df.copy()
            w_df["timestamp"] = pd.to_datetime(w_df["timestamp"], utc=True)
            w_df = w_df.sort_values(by="timestamp").reset_index(drop=True)
            w_cols = [
                "timestamp", "temperature", "humidity", "cloud_cover", "wind_speed",
                "solar_irradiance_proxy", "heat_index", "cooling_degree_metric", "heating_degree_metric"
            ]
            w_cols = [c for c in w_cols if c in w_df.columns]
            combined = pd.merge_asof(e_df, w_df[w_cols], on="timestamp", direction="backward")
            for c in ["temperature", "humidity", "cloud_cover", "wind_speed", "solar_irradiance_proxy", "heat_index", "cooling_degree_metric", "heating_degree_metric"]:
                if c in combined.columns:
                    combined[c] = combined[c].ffill().bfill()
        else:
            combined = e_df
        base_tariff = 4.7
        if tariff_df is not None and not tariff_df.empty:
            dom_rates = tariff_df[tariff_df["category"].str.contains("Domestic", na=False)]
            if not dom_rates.empty:
                try:
                    base_tariff = float(dom_rates.iloc[0].get("rate_per_unit_inr", 4.7))
                    if base_tariff == 0.0 and len(dom_rates) > 1:
                        base_tariff = float(dom_rates.iloc[1].get("rate_per_unit_inr", 4.7))
                except Exception:
                    base_tariff = 4.7
        combined["electricity_tariff_rate"] = base_tariff
        combined["estimated_interval_cost_inr"] = np.round(combined["energy_usage"] * 0.25 * combined["electricity_tariff_rate"], 4)
        
        # Interaction feature: solar to demand ratio
        if "solar_irradiance_proxy" in combined.columns and "energy_usage" in combined.columns:
            combined["solar_load_ratio"] = np.round(combined["solar_irradiance_proxy"] / (combined["energy_usage"] * 1000.0 + 1e-4), 3)

        target_order = [
            "timestamp", "temperature", "humidity", "cloud_cover", "wind_speed",
            "solar_irradiance_proxy", "heat_index", "cooling_degree_metric", "heating_degree_metric",
            "energy_usage", "previous_energy_usage", "lag_1", "lag_2", "lag_3", "lag_4", "lag_8", "lag_12",
            "rolling_mean_4", "rolling_std_4", "rolling_mean_8", "rolling_max_8", "rolling_min_8",
            "peak_to_average_ratio", "ema_4", "solar_load_ratio",
            "hour", "day", "month", "weekday", "is_weekend", "sin_hour", "cos_hour",
            "electricity_tariff_rate", "estimated_interval_cost_inr"
        ]
        final_cols = [c for c in target_order if c in combined.columns]
        return combined[final_cols].reset_index(drop=True)
