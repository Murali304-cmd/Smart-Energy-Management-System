import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib
logger = logging.getLogger('SEMS.LoadLSTM')
SEQUENCE_LENGTH = 12

class LoadLSTMNetwork(nn.Module):

    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super(LoadLSTMNetwork, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.layer_norm = nn.LayerNorm(hidden_dim * 2)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.SiLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, _ = self.lstm(x)
        last_step = self.layer_norm(lstm_out[:, -1, :])
        out = self.fc(last_step)
        return out

class LoadLSTMModel:

    def __init__(
        self,
        target_column: str = "energy_usage",
        feature_columns: Optional[List[str]] = None,
        sequence_length: int = SEQUENCE_LENGTH,
        hidden_dim: int = 64,
        num_layers: int = 2,
        learning_rate: float = 0.003,
        epochs: int = 80,
        batch_size: int = 32
    ):
        self.target_column = target_column
        self.feature_columns = feature_columns or [
            "energy_usage", "previous_energy_usage", "lag_1", "lag_2", "lag_3", "lag_4", "lag_8", "lag_12",
            "rolling_mean_4", "rolling_std_4", "rolling_mean_8", "peak_to_average_ratio", "ema_4",
            "hour", "weekday", "month", "is_weekend", "sin_hour", "cos_hour"
        ]
        self.sequence_length = sequence_length
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.model: Optional[LoadLSTMNetwork] = None
        self.feature_scaler: Optional[StandardScaler] = None
        self.target_scaler: Optional[StandardScaler] = None
        self.is_trained = False

    def _create_sequences(self, features: np.ndarray, targets: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X_seq, y_seq = ([], [])
        n_samples = len(features)
        for i in range(self.sequence_length, n_samples):
            X_seq.append(features[i - self.sequence_length:i])
            y_seq.append(targets[i])
        return (np.array(X_seq, dtype=np.float32), np.array(y_seq, dtype=np.float32))

    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        if df.empty:
            return (False, 'Energy dataset is empty.')
        if self.target_column not in df.columns:
            return (False, f"Required target column '{self.target_column}' is missing from energy dataset.")
        if len(df) <= self.sequence_length + 5:
            return (False, f'Not enough data points ({len(df)}) for sequence length {self.sequence_length}.')
        available_features = [f for f in self.feature_columns if f in df.columns]
        if not available_features:
            return (False, 'No required load features are present in dataset.')
        if self.target_column in available_features:
            available_features.remove(self.target_column)
            available_features.insert(0, self.target_column)
        self.feature_columns = available_features
        return (True, 'Energy dataset validated successfully.')

    def prepare_data(self, df: pd.DataFrame, train_ratio: float=0.7, val_ratio: float=0.15) -> Optional[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
        valid, msg = self.validate_data(df)
        if not valid:
            logger.warning(msg)
            return None
        if 'timestamp' in df.columns:
            df = df.sort_values(by='timestamp').reset_index(drop=True)
        n_samples = len(df)
        train_end = int(n_samples * train_ratio)
        train_df = df.iloc[:train_end]
        self.feature_scaler = StandardScaler()
        self.target_scaler = StandardScaler()
        self.feature_scaler.fit(train_df[self.feature_columns].values)
        self.target_scaler.fit(train_df[[self.target_column]].values)
        all_feats = self.feature_scaler.transform(df[self.feature_columns].values)
        all_targets = self.target_scaler.transform(df[[self.target_column]].values)
        X_all, y_all = self._create_sequences(all_feats, all_targets)
        total_sequences = len(X_all)
        if total_sequences < 3:
            logger.warning('Not enough sequences generated.')
            return None
        seq_train_end = max(1, int(total_sequences * train_ratio))
        seq_val_end = max(seq_train_end + 1, int(total_sequences * (train_ratio + val_ratio)))
        seq_val_end = min(seq_val_end, total_sequences - 1)
        X_train, y_train = (X_all[:seq_train_end], y_all[:seq_train_end])
        X_val, y_val = (X_all[seq_train_end:seq_val_end], y_all[seq_train_end:seq_val_end])
        X_test, y_test = (X_all[seq_val_end:], y_all[seq_val_end:])
        if len(X_test) == 0:
            X_test, y_test = (X_val, y_val)
        return (torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32), torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.float32), torch.tensor(X_test, dtype=torch.float32), torch.tensor(y_test, dtype=torch.float32))

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        data_splits = self.prepare_data(df)
        if data_splits is None:
            return {'status': 'error', 'message': 'Failed to prepare sequential data for Load LSTM.'}
        X_train, y_train, X_val, y_val, X_test, y_test = data_splits
        input_dim = X_train.shape[2]
        self.model = LoadLSTMNetwork(input_dim=input_dim, hidden_dim=self.hidden_dim, num_layers=self.num_layers)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate, weight_decay=1e-05)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)
        best_val_loss = float('inf')
        best_weights = None
        patience = 12
        patience_counter = 0
        train_dataset = torch.utils.data.TensorDataset(X_train, y_train)
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=self.batch_size, shuffle=False)
        for epoch in range(self.epochs):
            self.model.train()
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                pred = self.model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
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
        return {'status': 'success', 'target': self.target_column, 'sequence_length': self.sequence_length, 'features': self.feature_columns, 'metrics': metrics}

    def evaluate(self, X_test: torch.Tensor, y_test: torch.Tensor) -> Dict[str, float]:
        if not self.is_trained or self.model is None:
            raise RuntimeError('Model is not trained.')
        self.model.eval()
        with torch.no_grad():
            pred_scaled = self.model(X_test).numpy()
            y_test_scaled = y_test.numpy()
        y_pred = self.target_scaler.inverse_transform(pred_scaled).flatten()
        y_true = self.target_scaler.inverse_transform(y_test_scaled).flatten()
        y_pred = np.maximum(0.05, y_pred)
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))
        return {'MAE': round(mae, 3), 'RMSE': round(rmse, 3), 'R2': round(r2, 4)}

    def predict(self, recent_sequence: pd.DataFrame) -> float:
        if not self.is_trained or self.model is None or self.feature_scaler is None:
            raise RuntimeError('Load LSTM model is not trained or loaded.')
        if len(recent_sequence) < self.sequence_length:
            raise ValueError(f'Need at least {self.sequence_length} recent readings to forecast load, got {len(recent_sequence)}.')
        missing = [f for f in self.feature_columns if f not in recent_sequence.columns]
        if missing:
            raise ValueError(f'Required feature missing: {missing[0]}')
        seq_window = recent_sequence.iloc[-self.sequence_length:][self.feature_columns].values
        scaled_seq = self.feature_scaler.transform(seq_window)
        x_tensor = torch.tensor(scaled_seq.reshape(1, self.sequence_length, -1), dtype=torch.float32)
        self.model.eval()
        with torch.no_grad():
            pred_scaled = self.model(x_tensor).numpy()
        pred_actual = self.target_scaler.inverse_transform(pred_scaled).flatten()[0]
        return float(max(0.05, round(pred_actual, 3)))

    def save(self, save_dir: Path):
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        model_path = save_dir / 'load_lstm.pt'
        meta_path = save_dir / 'load_lstm_meta.joblib'
        if self.model is not None:
            torch.save(self.model.state_dict(), model_path)
            joblib.dump({'target_column': self.target_column, 'feature_columns': self.feature_columns, 'sequence_length': self.sequence_length, 'hidden_dim': self.hidden_dim, 'num_layers': self.num_layers, 'feature_scaler': self.feature_scaler, 'target_scaler': self.target_scaler, 'input_dim': len(self.feature_columns)}, meta_path)
            logger.info(f'Load LSTM model and scalers saved to {save_dir}')

    def load(self, save_dir: Path):
        save_dir = Path(save_dir)
        model_path = save_dir / 'load_lstm.pt'
        meta_path = save_dir / 'load_lstm_meta.joblib'
        if not model_path.exists() or not meta_path.exists():
            raise FileNotFoundError(f'Trained Load LSTM model artifacts not found at {save_dir}')
        meta = joblib.load(meta_path)
        self.target_column = meta['target_column']
        self.feature_columns = meta['feature_columns']
        self.sequence_length = meta['sequence_length']
        self.hidden_dim = meta['hidden_dim']
        self.num_layers = meta['num_layers']
        self.feature_scaler = meta['feature_scaler']
        self.target_scaler = meta['target_scaler']
        self.model = LoadLSTMNetwork(input_dim=meta['input_dim'], hidden_dim=self.hidden_dim, num_layers=self.num_layers)
        self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        self.model.eval()
        self.is_trained = True
        logger.info('Load LSTM model successfully loaded.')
