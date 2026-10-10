import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
import xgboost as xgb
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SEMS.RetrainImprovedModels")

ARTIFACT_DIR = Path(r"C:\Users\mural\.gemini\antigravity-ide\brain\ef5499b0-9c54-4e91-9d83-434200f03153")
TRAINED_MODELS_DIR = BASE_DIR / "trained_models"
TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR = BASE_DIR / "data" / "processed"

from models.solar_mlp import SolarMLPNetwork
from models.load_lstm import LoadLSTMModel, LoadLSTMNetwork
from models.price_xgboost import PriceXGBoostModel

def run_retraining():
    logger.info("==================================================")
    logger.info("STEP 1: RETRAINING SOLAR IRRADIANCE MODEL (AUTHENTIC GHI)")
    logger.info("==================================================")
    weather_csv = PROCESSED_DIR / "weather_processed.csv"
    df_w = pd.read_csv(weather_csv)
    
    solar_features = [
        "temperature", "humidity", "cloud_cover", "wind_speed", "heat_index",
        "cooling_degree_metric", "hour", "month", "weekday", "sin_hour", "cos_hour",
        "sin_month", "cos_month"
    ]
    solar_target = "solar_irradiance"
    
    n_w = len(df_w)
    tr_end_w = int(0.70 * n_w)
    val_end_w = int(0.85 * n_w)
    
    train_w = df_w.iloc[:tr_end_w]
    val_w = df_w.iloc[tr_end_w:val_end_w]
    test_w = df_w.iloc[val_end_w:].copy().reset_index(drop=True)
    
    # Night mask: Chennai daylight is 06:00 to 18:00
    day_train_w = train_w[train_w["hour"].between(6, 18)]
    day_val_w = val_w[val_w["hour"].between(6, 18)]
    
    scaler_solar_X = MinMaxScaler()
    scaler_solar_y = MinMaxScaler()
    X_tr_s = scaler_solar_X.fit_transform(day_train_w[solar_features].values)
    y_tr_s = scaler_solar_y.fit_transform(day_train_w[[solar_target]].values)
    X_val_s = scaler_solar_X.transform(day_val_w[solar_features].values)
    y_val_s = scaler_solar_y.transform(day_val_w[[solar_target]].values)
    
    # Train Solar MLP
    solar_mlp_net = SolarMLPNetwork(input_dim=len(solar_features), hidden_dim1=64, hidden_dim2=32)
    criterion_s = nn.HuberLoss(delta=1.0)
    optimizer_s = optim.Adam(solar_mlp_net.parameters(), lr=0.005, weight_decay=1e-4)
    scheduler_s = optim.lr_scheduler.ReduceLROnPlateau(optimizer_s, mode="min", factor=0.5, patience=5)
    
    train_loader_s = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(torch.tensor(X_tr_s, dtype=torch.float32), torch.tensor(y_tr_s, dtype=torch.float32)),
        batch_size=32, shuffle=True
    )
    
    best_loss = float("inf")
    best_weights = None
    for epoch in range(80):
        solar_mlp_net.train()
        for bx, by in train_loader_s:
            optimizer_s.zero_grad()
            out = solar_mlp_net(bx)
            loss = criterion_s(out, by)
            loss.backward()
            optimizer_s.step()
        
        solar_mlp_net.eval()
        with torch.no_grad():
            v_loss = criterion_s(solar_mlp_net(torch.tensor(X_val_s, dtype=torch.float32)), torch.tensor(y_val_s, dtype=torch.float32)).item()
        scheduler_s.step(v_loss)
        if v_loss < best_loss:
            best_loss = v_loss
            best_weights = solar_mlp_net.state_dict().copy()
            
    if best_weights:
        solar_mlp_net.load_state_dict(best_weights)
        
    # Evaluate on full test set with nighttime masking
    test_day_mask = test_w["hour"].between(6, 18).values
    solar_test_pred = np.zeros(len(test_w), dtype=np.float32)
    if np.any(test_day_mask):
        day_test_X = test_w.loc[test_day_mask, solar_features].values
        day_test_s = scaler_solar_X.transform(day_test_X)
        solar_mlp_net.eval()
        with torch.no_grad():
            pred_s = solar_mlp_net(torch.tensor(day_test_s, dtype=torch.float32)).numpy()
        pred_inv = scaler_solar_y.inverse_transform(pred_s).flatten()
        solar_test_pred[test_day_mask] = np.clip(pred_inv, 0.0, None)
        
    solar_y_true = test_w[solar_target].values
    solar_mae = float(mean_absolute_error(solar_y_true, solar_test_pred))
    solar_rmse = float(np.sqrt(mean_squared_error(solar_y_true, solar_test_pred)))
    solar_r2 = float(r2_score(solar_y_true, solar_test_pred))
    solar_wape = float((np.sum(np.abs(solar_y_true - solar_test_pred)) / np.sum(solar_y_true)) * 100.0)
    day_mask_calc = solar_y_true > 10.0
    solar_mape = float(np.mean(np.abs((solar_y_true[day_mask_calc] - solar_test_pred[day_mask_calc]) / solar_y_true[day_mask_calc])) * 100.0)
    
    logger.info(f"Retrained Solar MLP -> MAE: {solar_mae:.3f} W/m², RMSE: {solar_rmse:.3f} W/m², R²: {solar_r2:.4f}, WAPE: {solar_wape:.2f}%, Daytime MAPE: {solar_mape:.2f}%")
    
    # Save Solar MLP model & metadata
    torch.save(solar_mlp_net.state_dict(), TRAINED_MODELS_DIR / "solar_mlp.pt")
    joblib.dump({
        "target_column": solar_target,
        "feature_columns": solar_features,
        "feature_scaler": scaler_solar_X,
        "target_scaler": scaler_solar_y,
        "input_dim": len(solar_features),
        "night_mask_applied": True,
        "metrics": {"MAE": round(solar_mae, 3), "RMSE": round(solar_rmse, 3), "R2": round(solar_r2, 4), "WAPE": round(solar_wape, 2), "MAPE": round(solar_mape, 2)}
    }, TRAINED_MODELS_DIR / "solar_mlp_meta.joblib")
    
    # Plot Actual vs Predicted Solar
    plt.figure(figsize=(10, 4.5))
    plot_len = min(168, len(solar_y_true)) # 7 days
    plt.plot(solar_y_true[:plot_len], label="Actual GHI (W/m²)", color="#f59e0b", lw=2)
    plt.plot(solar_test_pred[:plot_len], label=f"Predicted Solar MLP (R² = {solar_r2:.4f})", color="#0284c7", lw=1.5, linestyle="--")
    plt.title("Solar MLP: Actual vs Predicted Solar Irradiance (7 Days Unseen Test Data)")
    plt.xlabel("Hours")
    plt.ylabel("Irradiance (W/m²)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ARTIFACT_DIR / "solar_actual_vs_predicted.png", dpi=200)
    plt.close()
    
    logger.info("==================================================")
    logger.info("STEP 2: RETRAINING LOAD LSTM & BASELINES")
    logger.info("==================================================")
    energy_csv = PROCESSED_DIR / "energy_processed.csv"
    df_e = pd.read_csv(energy_csv)
    
    load_model = LoadLSTMModel(epochs=60, learning_rate=0.003)
    res_load = load_model.train(df_e)
    load_model.save(TRAINED_MODELS_DIR)
    
    # Get exact predictions on test
    splits = load_model.prepare_data(df_e)
    X_tr_l, y_tr_l, X_val_l, y_val_l, X_te_l, y_te_l = splits
    load_model.model.eval()
    with torch.no_grad():
        preds_scaled = load_model.model(X_te_l).numpy()
    load_test_pred = load_model.target_scaler.inverse_transform(preds_scaled).flatten()
    load_y_true = load_model.target_scaler.inverse_transform(y_te_l.numpy()).flatten()
    
    load_mae = float(mean_absolute_error(load_y_true, load_test_pred))
    load_rmse = float(np.sqrt(mean_squared_error(load_y_true, load_test_pred)))
    load_r2 = float(r2_score(load_y_true, load_test_pred))
    load_mape = float(np.mean(np.abs((load_y_true - load_test_pred) / load_y_true)) * 100.0)
    load_wape = float((np.sum(np.abs(load_y_true - load_test_pred)) / np.sum(load_y_true)) * 100.0)
    
    logger.info(f"Retrained Load LSTM -> MAE: {load_mae:.3f} kW, RMSE: {load_rmse:.3f} kW, R²: {load_r2:.4f}, MAPE: {load_mape:.2f}%, WAPE: {load_wape:.2f}%")
    
    # Plot Actual vs Predicted Load
    plt.figure(figsize=(10, 4.5))
    plot_len_load = min(144, len(load_y_true)) # 3 days (48 steps/day)
    plt.plot(load_y_true[:plot_len_load], label="Actual Load (kW)", color="#10b981", lw=2)
    plt.plot(load_test_pred[:plot_len_load], label=f"Predicted Load LSTM (R² = {load_r2:.4f})", color="#6366f1", lw=1.5, linestyle="--")
    plt.title("Load LSTM: Actual vs Predicted Load Demand (3 Days Unseen Test Data)")
    plt.xlabel("Time Step (30-min Intervals)")
    plt.ylabel("Load (kW)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ARTIFACT_DIR / "load_actual_vs_predicted.png", dpi=200)
    plt.close()
    
    logger.info("==================================================")
    logger.info("STEP 3: TUNING & EVALUATING PRICE XGBOOST MODEL")
    logger.info("==================================================")
    tneb_csv = PROCESSED_DIR / "tneb_processed.csv"
    df_tneb = pd.read_csv(tneb_csv)
    
    price_model = PriceXGBoostModel(n_estimators=120, max_depth=4, learning_rate=0.04)
    res_price = price_model.train(df_tneb)
    price_model.save(TRAINED_MODELS_DIR)
    
    splits_p = price_model.prepare_data(df_tneb)
    X_tr_p, y_tr_p, X_val_p, y_val_p, X_te_p, y_te_p = splits_p
    price_preds = price_model.model.predict(X_te_p)
    price_preds = np.maximum(0.0, price_preds)
    
    price_mae = float(mean_absolute_error(y_te_p, price_preds))
    price_rmse = float(np.sqrt(mean_squared_error(y_te_p, price_preds)))
    price_r2 = float(r2_score(y_te_p, price_preds))
    price_wape = float((np.sum(np.abs(y_te_p - price_preds)) / np.sum(y_te_p)) * 100.0)
    non_zero = y_te_p > 0.1
    price_mape = float(np.mean(np.abs((y_te_p[non_zero] - price_preds[non_zero]) / y_te_p[non_zero])) * 100.0)
    
    logger.info(f"Retrained Price XGBoost -> MAE: ₹{price_mae:.3f}/unit, RMSE: ₹{price_rmse:.3f}/unit, R²: {price_r2:.4f}, MAPE: {price_mape:.2f}%, WAPE: {price_wape:.2f}%")
    
    # Plot Actual vs Predicted Price
    plt.figure(figsize=(9, 4.5))
    indices = np.arange(len(y_te_p))
    plt.scatter(indices, y_te_p, color="#dc2626", label="Actual Tariff (₹/unit)", s=40, zorder=3)
    plt.plot(indices, price_preds, color="#2563eb", label=f"Predicted XGBoost (R² = {price_r2:.4f})", linestyle="--", lw=1.5)
    plt.title("Price XGBoost: Actual vs Predicted Effective Tariff Rate")
    plt.xlabel("Test Sample Index")
    plt.ylabel("Tariff Rate (₹/kWh)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ARTIFACT_DIR / "price_actual_vs_predicted.png", dpi=200)
    plt.close()
    
    # Update metadata.json
    metadata = {
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_protocol": "Chronological 70% Train / 15% Validation / 15% Test split with strictly zero future leakage",
        "models": {
            "solar_mlp": {
                "target": solar_target,
                "model_type": "Multi-Layer Perceptron (PyTorch) with Astronomical Night Masking",
                "features": solar_features,
                "test_samples": len(test_w),
                "metrics": {
                    "MAE": round(solar_mae, 3),
                    "RMSE": round(solar_rmse, 3),
                    "R2": round(solar_r2, 4),
                    "WAPE": round(solar_wape, 2),
                    "Daytime_MAPE": round(solar_mape, 2)
                }
            },
            "load_lstm": {
                "target": "energy_usage",
                "model_type": "Deep Bidirectional LSTM with Multi-Lag Feature Engineering",
                "sequence_length": 12,
                "features": load_model.feature_columns,
                "test_samples": len(load_y_true),
                "metrics": {
                    "MAE": round(load_mae, 3),
                    "RMSE": round(load_rmse, 3),
                    "R2": round(load_r2, 4),
                    "MAPE": round(load_mape, 2),
                    "WAPE": round(load_wape, 2)
                }
            },
            "price_xgboost": {
                "target": "effective_cost_per_unit",
                "model_type": "Gradient Boosted Regression Trees (XGBoost)",
                "features": price_model.feature_columns,
                "test_samples": len(y_te_p),
                "metrics": {
                    "MAE": round(price_mae, 3),
                    "RMSE": round(price_rmse, 3),
                    "R2": round(price_r2, 4),
                    "MAPE": round(price_mape, 2),
                    "WAPE": round(price_wape, 2)
                }
            }
        }
    }
    
    meta_json_path = TRAINED_MODELS_DIR / "metadata.json"
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    logger.info(f"Saved consolidated verified metadata to {meta_json_path}")
    print("\n=======================================================")
    print("ALL ML MODELS RETRAINED, EVALUATED, AND SAVED SUCCESSFULLY")
    print("=======================================================")

if __name__ == "__main__":
    run_retraining()
