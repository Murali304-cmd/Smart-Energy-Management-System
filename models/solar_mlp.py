import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
import joblib
logger = logging.getLogger('SEMS.SolarMLP')
SOLAR_TARGET_COLUMN = os.getenv('SOLAR_TARGET_COLUMN', 'solar_irradiance_proxy')

class SolarMLPNetwork(nn.Module):

    def __init__(self, input_dim: int, hidden_dim1: int = 64, hidden_dim2: int = 32, dropout_rate: float = 0.1):
        super(SolarMLPNetwork, self).__init__()
        self.block1 = nn.Sequential(
            nn.Linear(input_dim, hidden_dim1),
            nn.BatchNorm1d(hidden_dim1),
            nn.SiLU(),
            nn.Dropout(dropout_rate)
        )
        self.block2 = nn.Sequential(
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.BatchNorm1d(hidden_dim2),
            nn.SiLU()
        )
        self.skip = nn.Linear(input_dim, hidden_dim2) if input_dim != hidden_dim2 else nn.Identity()
        self.head = nn.Linear(hidden_dim2, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h1 = self.block1(x)
        h2 = self.block2(h1)
        res = self.skip(x)
        out = self.head(h2 + res)
        return out

class SolarMLPModel:

    def __init__(
        self,
        target_column: str = SOLAR_TARGET_COLUMN,
        feature_columns: Optional[List[str]] = None,
        learning_rate: float = 0.005,
        epochs: int = 100,
        batch_size: int = 32
    ):
        self.target_column = target_column
        self.feature_columns = feature_columns or [
            "temperature", "humidity", "cloud_cover", "wind_speed", "heat_index",
            "cooling_degree_metric", "heating_degree_metric",
            "hour", "day", "month", "weekday", "is_weekend", "sin_hour", "cos_hour"
        ]
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.model: Optional[SolarMLPNetwork] = None
        self.feature_scaler: Optional[MinMaxScaler] = None
        self.target_scaler: Optional[MinMaxScaler] = None
        self.is_trained = False
        self.target_available = True

    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        if df.empty:
            return (False, 'Weather dataset is empty.')
        if self.target_column not in df.columns:
            alternate_targets = ['solar_generation', 'solar_generation_kw', 'solar_irradiance_proxy']
            found = False
            for alt in alternate_targets:
                if alt in df.columns:
                    self.target_column = alt
                    found = True
                    break
            if not found:
                self.target_available = False
                return (False, f"Solar generation target is unavailable. Target column '{self.target_column}' not found in dataset.")
        available_features = [f for f in self.feature_columns if f in df.columns and f != self.target_column]
        if not available_features:
            return (False, 'None of the required weather features are available.')
        self.feature_columns = available_features
        return (True, 'Data validation successful.')

    def prepare_data(self, df: pd.DataFrame, train_ratio: float=0.7, val_ratio: float=0.15) -> Optional[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
        valid, msg = self.validate_data(df)
        if not valid:
            logger.warning(msg)
            return None
        if 'timestamp' in df.columns:
            df = df.sort_values(by='timestamp').reset_index(drop=True)
        X_raw = df[self.feature_columns].values.astype(np.float32)
        y_raw = df[self.target_column].values.reshape(-1, 1).astype(np.float32)
        n_samples = len(df)
        train_end = int(n_samples * train_ratio)
        val_end = int(n_samples * (train_ratio + val_ratio))
        X_train_raw = X_raw[:train_end]
        y_train_raw = y_raw[:train_end]
        X_val_raw = X_raw[train_end:val_end]
        y_val_raw = y_raw[train_end:val_end]
        X_test_raw = X_raw[val_end:]
        y_test_raw = y_raw[val_end:]
        self.feature_scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        X_train = self.feature_scaler.fit_transform(X_train_raw)
        y_train = self.target_scaler.fit_transform(y_train_raw)
        X_val = self.feature_scaler.transform(X_val_raw)
        y_val = self.target_scaler.transform(y_val_raw)
        X_test = self.feature_scaler.transform(X_test_raw)
        y_test = self.target_scaler.transform(y_test_raw)
        return (torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32), torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.float32), torch.tensor(X_test, dtype=torch.float32), torch.tensor(y_test, dtype=torch.float32))

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        data_splits = self.prepare_data(df)
        if data_splits is None:
            return {'status': 'error', 'message': 'Solar generation target is unavailable.'}
        X_train, y_train, X_val, y_val, X_test, y_test = data_splits
        input_dim = X_train.shape[1]
        self.model = SolarMLPNetwork(input_dim=input_dim)
        criterion = nn.HuberLoss(delta=1.0)
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate, weight_decay=0.0001)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)
        best_val_loss = float('inf')
        best_weights = None
        patience = 12
        patience_counter = 0
        train_dataset = torch.utils.data.TensorDataset(X_train, y_train)
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        for epoch in range(self.epochs):
            self.model.train()
            epoch_loss = 0.0
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                pred = self.model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * len(batch_x)
            self.model.eval()
            with torch.no_grad():
                val_pred = self.model(X_val)
                val_loss = criterion(val_pred, y_val).item()
            scheduler.step(val_loss)
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_weights = self.model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    break
        if best_weights is not None:
            self.model.load_state_dict(best_weights)
        self.is_trained = True
        metrics = self.evaluate(X_test, y_test)
        return {'status': 'success', 'target': self.target_column, 'features': self.feature_columns, 'metrics': metrics}

    def evaluate(self, X_test: torch.Tensor, y_test: torch.Tensor) -> Dict[str, float]:
        if not self.is_trained or self.model is None:
            raise RuntimeError('Model is not trained.')
        self.model.eval()
        with torch.no_grad():
            pred_scaled = self.model(X_test).numpy()
            y_test_scaled = y_test.numpy()
        y_pred = self.target_scaler.inverse_transform(pred_scaled).flatten()
        y_true = self.target_scaler.inverse_transform(y_test_scaled).flatten()
        y_pred = np.maximum(0.0, y_pred)
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))
        return {'MAE': round(mae, 3), 'RMSE': round(rmse, 3), 'R2': round(r2, 4)}

    def predict(self, input_features: pd.DataFrame) -> np.ndarray:
        if not self.is_trained or self.model is None or self.feature_scaler is None:
            raise RuntimeError('Solar MLP model is not trained or loaded.')
        input_features = input_features.copy()
        if 'month' in input_features.columns:
            if 'sin_month' not in input_features.columns:
                input_features['sin_month'] = np.sin(2.0 * np.pi * (input_features['month'] - 1) / 12.0)
            if 'cos_month' not in input_features.columns:
                input_features['cos_month'] = np.cos(2.0 * np.pi * (input_features['month'] - 1) / 12.0)
        if 'hour' in input_features.columns:
            if 'sin_hour' not in input_features.columns:
                input_features['sin_hour'] = np.sin(2.0 * np.pi * input_features['hour'] / 24.0)
            if 'cos_hour' not in input_features.columns:
                input_features['cos_hour'] = np.cos(2.0 * np.pi * input_features['hour'] / 24.0)
        missing = [f for f in self.feature_columns if f not in input_features.columns]
        if missing:
            raise ValueError(f'Required feature missing: {missing[0]}')
        X_raw = input_features[self.feature_columns].values.astype(np.float32)
        X_scaled = self.feature_scaler.transform(X_raw)
        self.model.eval()
        with torch.no_grad():
            pred_scaled = self.model(torch.tensor(X_scaled, dtype=torch.float32)).numpy()
        pred_actual = self.target_scaler.inverse_transform(pred_scaled).flatten()
        return np.maximum(0.0, np.round(pred_actual, 3))

    def save(self, save_dir: Path):
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        model_path = save_dir / 'solar_mlp.pt'
        meta_path = save_dir / 'solar_mlp_meta.joblib'
        if self.model is not None:
            torch.save(self.model.state_dict(), model_path)
            joblib.dump({'target_column': self.target_column, 'feature_columns': self.feature_columns, 'feature_scaler': self.feature_scaler, 'target_scaler': self.target_scaler, 'input_dim': len(self.feature_columns)}, meta_path)
            logger.info(f'Solar MLP model and scalers saved to {save_dir}')

    def load(self, save_dir: Path):
        save_dir = Path(save_dir)
        model_path = save_dir / 'solar_mlp.pt'
        meta_path = save_dir / 'solar_mlp_meta.joblib'
        if not model_path.exists() or not meta_path.exists():
            raise FileNotFoundError(f'Trained Solar MLP model artifacts not found at {save_dir}')
        meta = joblib.load(meta_path)
        self.target_column = meta['target_column']
        self.feature_columns = meta['feature_columns']
        self.feature_scaler = meta['feature_scaler']
        self.target_scaler = meta['target_scaler']
        self.model = SolarMLPNetwork(input_dim=meta['input_dim'])
        self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        self.model.eval()
        self.is_trained = True
        logger.info('Solar MLP model successfully loaded.')
