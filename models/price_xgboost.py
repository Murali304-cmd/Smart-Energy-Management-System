import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib
logger = logging.getLogger('SEMS.PriceXGBoost')

class PriceXGBoostModel:

    def __init__(self, target_column: str='effective_cost_per_unit', feature_columns: Optional[List[str]]=None, n_estimators: int=120, max_depth: int=4, learning_rate: float=0.05):
        self.target_column = target_column
        self.feature_columns = feature_columns or ['units_consumed', 'previous_reading', 'current_reading', 'tariff_tier_code', 'prev_cycle_units', 'consumption_trend', 'month', 'weekday']
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_scaler: Optional[StandardScaler] = None
        self.is_trained = False
        self.target_available = True

    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        if df.empty:
            return (False, 'TNEB dataset is empty.')
        if self.target_column not in df.columns:
            alternates = ['effective_cost_per_unit', 'electricity_cost', 'bill_amount']
            found = False
            for alt in alternates:
                if alt in df.columns:
                    self.target_column = alt
                    found = True
                    break
            if not found:
                self.target_available = False
                return (False, 'No valid electricity price target was found in the TNEB dataset.')
        valid_series = pd.to_numeric(df[self.target_column], errors='coerce').dropna()
        if len(valid_series) == 0 or (valid_series == 0).all():
            self.target_available = False
            return (False, 'No valid electricity price target was found in the TNEB dataset.')
        available_features = [f for f in self.feature_columns if f in df.columns and f != self.target_column]
        if not available_features:
            return (False, 'No valid historical TNEB features found for price prediction.')
        self.feature_columns = available_features
        return (True, 'TNEB price data validated.')

    def prepare_data(self, df: pd.DataFrame, train_ratio: float=0.7, val_ratio: float=0.15) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        valid, msg = self.validate_data(df)
        if not valid:
            logger.warning(msg)
            return None
        date_col = 'billing_date' if 'billing_date' in df.columns else 'date' if 'date' in df.columns else None
        if date_col:
            df = df.sort_values(by=date_col).reset_index(drop=True)
        clean_df = df.dropna(subset=[self.target_column] + self.feature_columns).copy()
        n_samples = len(clean_df)
        if n_samples < 15:
            logger.warning('Not enough TNEB records to perform 3-way split.')
            return None
        train_end = int(n_samples * train_ratio)
        val_end = int(n_samples * (train_ratio + val_ratio))
        train_df = clean_df.iloc[:train_end]
        val_df = clean_df.iloc[train_end:val_end]
        test_df = clean_df.iloc[val_end:]
        self.feature_scaler = StandardScaler()
        X_train_raw = train_df[self.feature_columns].values.astype(np.float32)
        y_train = train_df[self.target_column].values.astype(np.float32)
        X_val_raw = val_df[self.feature_columns].values.astype(np.float32)
        y_val = val_df[self.target_column].values.astype(np.float32)
        X_test_raw = test_df[self.feature_columns].values.astype(np.float32)
        y_test = test_df[self.target_column].values.astype(np.float32)
        X_train = self.feature_scaler.fit_transform(X_train_raw)
        X_val = self.feature_scaler.transform(X_val_raw)
        X_test = self.feature_scaler.transform(X_test_raw)
        return (X_train, y_train, X_val, y_val, X_test, y_test)

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        splits = self.prepare_data(df)
        if splits is None:
            return {'status': 'error', 'message': 'No valid electricity price target was found in the TNEB dataset.'}
        X_train, y_train, X_val, y_val, X_test, y_test = splits
        self.model = xgb.XGBRegressor(n_estimators=self.n_estimators, max_depth=self.max_depth, learning_rate=self.learning_rate, subsample=0.85, colsample_bytree=0.85, random_state=42, objective='reg:squarederror')
        self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        self.is_trained = True
        metrics = self.evaluate(X_test, y_test)
        return {'status': 'success', 'target': self.target_column, 'features': self.feature_columns, 'metrics': metrics}

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        if not self.is_trained or self.model is None:
            raise RuntimeError('XGBoost Price model is not trained.')
        y_pred = self.model.predict(X_test)
        y_pred = np.maximum(0.0, y_pred)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        return {'MAE': round(mae, 3), 'RMSE': round(rmse, 3), 'R2': round(r2, 4)}

    def predict(self, input_features: pd.DataFrame) -> np.ndarray:
        if not self.is_trained or self.model is None or self.feature_scaler is None:
            raise RuntimeError('Price XGBoost model is not trained or loaded.')
        missing = [f for f in self.feature_columns if f not in input_features.columns]
        if missing:
            raise ValueError(f'Required feature missing: {missing[0]}')
        X_raw = input_features[self.feature_columns].values.astype(np.float32)
        X_scaled = self.feature_scaler.transform(X_raw)
        pred = self.model.predict(X_scaled)
        return np.maximum(0.0, np.round(pred, 2))

    def save(self, save_dir: Path):
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        model_path = save_dir / 'price_xgboost.pkl'
        meta_path = save_dir / 'price_xgboost_meta.joblib'
        if self.model is not None:
            joblib.dump(self.model, model_path)
            joblib.dump({'target_column': self.target_column, 'feature_columns': self.feature_columns, 'feature_scaler': self.feature_scaler, 'n_estimators': self.n_estimators, 'max_depth': self.max_depth}, meta_path)
            logger.info(f'Price XGBoost model and scalers saved to {save_dir}')

    def load(self, save_dir: Path):
        save_dir = Path(save_dir)
        model_path = save_dir / 'price_xgboost.pkl'
        meta_path = save_dir / 'price_xgboost_meta.joblib'
        if not model_path.exists() or not meta_path.exists():
            raise FileNotFoundError(f'Trained Price XGBoost model not found at {save_dir}')
        self.model = joblib.load(model_path)
        meta = joblib.load(meta_path)
        self.target_column = meta['target_column']
        self.feature_columns = meta['feature_columns']
        self.feature_scaler = meta['feature_scaler']
        self.is_trained = True
        logger.info('Price XGBoost model successfully loaded.')
