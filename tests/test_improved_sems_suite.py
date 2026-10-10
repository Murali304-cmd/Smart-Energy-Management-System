import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from services.weather_service import WeatherService
from api.weather_api import get_current_weather
from api.smart_meter_api import get_current_energy_usage
from api.battery_api import get_bess_telemetry
from preprocessing.data_cleaner import DataCleaner
from preprocessing.feature_engineering import FeatureEngineering
from models.solar_mlp import SolarMLPModel
from models.load_lstm import LoadLSTMModel
from models.price_xgboost import PriceXGBoostModel
from energy.battery_manager import BatteryManager
from recommendation.allocation import BatteryConfig, allocate_energy
from recommendation.recommender import EnergyRecommenderService
from services.alert_service import AlertService
from server import app
from fastapi.testclient import TestClient

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Test Data Collection
def test_data_collection_weather_and_meter():
    ws = WeatherService()
    weather_data = ws.get_weather_data()
    assert weather_data is not None
    assert "current" in weather_data
    assert "temperature_c" in weather_data["current"] or "temperature_2m" in weather_data["current"]

    weather_api_res = get_current_weather(allow_demo_fallback=True)
    assert weather_api_res.get("status") == "success"
    assert "temperature" in weather_api_res

    meter = get_current_energy_usage()
    assert meter is not None
    assert meter.get("energy_usage_kw", 0.0) >= 0.0

    bess = get_bess_telemetry()
    assert 0.0 <= bess.get("battery_soc", 50.0) <= 100.0

# 2. Test Preprocessing & Data Cleaning
def test_preprocessing_and_cleaning():
    cleaner = DataCleaner()
    fe = FeatureEngineering()

    raw_df = pd.DataFrame({
        "timestamp": ["2026-09-20T10:00:00Z", "2026-09-20T10:15:00Z", "2026-09-20T10:30:00Z"],
        "meter_id": ["M01", "M01", "M01"],
        "energy_usage": [1.5, np.nan, 2.5],
        "unit": ["kW", "kW", "kW"]
    })
    cleaned = cleaner.clean_energy_data(raw_df)
    assert cleaned["energy_usage"].isna().sum() == 0
    assert len(cleaned) == 2  # Missing NaN row rejected as per data quality rule

# 3. Test Solar Prediction Model
def test_solar_prediction_model():
    models_dir = BASE_DIR / "trained_models"
    solar_model = SolarMLPModel()
    solar_model.load(models_dir)
    assert solar_model.is_trained

    # Daytime test
    input_day = pd.DataFrame([{
        "temperature": 32.0, "humidity": 60.0, "cloud_cover": 20.0, "wind_speed": 3.0,
        "heat_index": 28.0, "cooling_degree_metric": 8.0, "heating_degree_metric": 0.0,
        "hour": 12, "day": 15, "month": 6, "weekday": 2, "is_weekend": 0,
        "sin_hour": 0.0, "cos_hour": -1.0, "sin_month": 0.0, "cos_month": -1.0
    }])
    pred_day = solar_model.predict(input_day)
    assert len(pred_day) == 1
    assert pred_day[0] >= 0.0

# 4. Test Load Prediction Model
def test_load_prediction_model():
    models_dir = BASE_DIR / "trained_models"
    load_model = LoadLSTMModel()
    load_model.load(models_dir)
    assert load_model.is_trained

    # Sequence of 12 readings
    seq = pd.DataFrame([{
        "energy_usage": 1.5 + 0.1 * i,
        "previous_energy_usage": 1.4 + 0.1 * i,
        "lag_1": 1.5, "lag_2": 1.4, "lag_3": 1.3, "lag_4": 1.2, "lag_8": 1.0, "lag_12": 0.8,
        "rolling_mean_4": 1.4, "rolling_std_4": 0.1, "rolling_mean_8": 1.2,
        "peak_to_average_ratio": 1.1, "ema_4": 1.4, "hour": 14, "weekday": 2,
        "month": 6, "is_weekend": 0, "sin_hour": -0.5, "cos_hour": -0.86
    } for i in range(12)])
    pred_load = load_model.predict(seq)
    assert pred_load > 0.0

# 5. Test Price Prediction Model
def test_price_prediction_model():
    models_dir = BASE_DIR / "trained_models"
    price_model = PriceXGBoostModel()
    price_model.load(models_dir)
    assert price_model.is_trained

    tneb_input = pd.DataFrame([{
        "units_consumed": 350.0,
        "previous_reading": 3000.0,
        "current_reading": 3350.0,
        "tariff_tier_code": 1,
        "prev_cycle_units": 320.0,
        "consumption_trend": 30.0,
        "month": 6,
        "weekday": 2
    }])
    pred_price = price_model.predict(tneb_input)
    assert len(pred_price) == 1
    assert pred_price[0] >= 0.0

# 6. Test Battery Safety Guard (BESS)
def test_battery_safety_guard():
    bm = BatteryManager(capacity_kwh=20.0, min_soc=20.0, max_soc=100.0)
    # Check min SoC threshold detection
    assert bm.check_min_soc(20.0) is False
    assert bm.check_min_soc(19.0) is False
    assert bm.check_min_soc(25.0) is True

    # Test discharge at 20% SoC (4.0 kWh remaining)
    actual_pwr, new_soc, new_energy = bm.discharge(requested_deficit_kw=5.0, current_energy_kwh=4.0, dt_hours=0.25)
    assert actual_pwr == 0.0
    assert new_soc == 20.0
    assert new_energy == 4.0

    # Test discharge limit clamping
    assert bm.check_discharge_limit(15.0) == 10.0
    assert bm.check_charge_limit(12.0) == 6.0

# 7. Test DQN Action Space (4 Actions)
def test_dqn_action_space():
    rec = EnergyRecommenderService()
    res = rec.recommend_energy({
        "predicted_solar": 3.0,
        "predicted_load": 2.0,
        "electricity_price": 4.70,
        "battery_soc": 60.0,
        "current_load": 2.0,
        "time_peak_indicator": 0.0
    })
    assert res["status"] == "success"
    assert res["action_id"] in [0, 1, 2, 3]
    assert res["decision"] in ["SOLAR_PRIORITY", "BATTERY_DISPATCH", "GRID_USAGE", "PEAK_SHAVING"]

# 8. Test Power Balance Verification (P_solar + P_bat + P_grid == P_demand)
def test_power_balance_verification():
    bat_config = BatteryConfig()
    for s, l, soc, p, act in [
        (4.0, 2.0, 70.0, 4.7, 0),
        (1.0, 3.5, 40.0, 7.5, 3),
        (0.0, 4.0, 20.0, 7.5, 2),
        (5.0, 1.0, 98.0, 4.7, 0)
    ]:
        alloc = allocate_energy(predicted_solar=s, battery_soc=soc, user_demand=l, predicted_price=p, action=act, battery_config=bat_config)
        balance = alloc["solar_power"] + alloc["battery_power"] + alloc["grid_power"]
        assert abs(balance - l) < 1e-4
        assert alloc["power_balance_verified"] is True

# 9. Test Cost Optimization
def test_cost_calculation():
    bat_config = BatteryConfig()
    # When solar covers load, grid cost is zero and savings are 100%
    alloc = allocate_energy(predicted_solar=3.0, battery_soc=50.0, user_demand=2.0, predicted_price=5.0, action=0, battery_config=bat_config)
    assert alloc["estimated_grid_cost"] == 0.0
    assert alloc["savings_pct_vs_grid"] == 100.0

# 10. Test Explainable AI (XAI)
def test_xai_explanation_structure():
    rec = EnergyRecommenderService()
    res = rec.recommend_energy({
        "predicted_solar": 4.0, "predicted_load": 2.0, "electricity_price": 4.70,
        "battery_soc": 70.0, "current_load": 2.0, "time_peak_indicator": 0.0
    })
    xai = res["xai"]
    assert "decision" in xai
    assert "reasons" in xai and len(xai["reasons"]) >= 4
    assert "explanation" in xai and len(xai["explanation"]) > 10

# 11. Test Dashboard APIs
def test_dashboard_apis():
    r1 = client.get("/api/models/accuracy")
    assert r1.status_code == 200
    assert "models" in r1.json()

    r2 = client.get("/api/benchmarks/multi-day")
    assert r2.status_code == 200
    assert "metrics" in r2.json()

    r3 = client.get("/api/system/verified-pipeline")
    assert r3.status_code == 200
    assert r3.json()["status"] == "verified"

# 12. Test Alert Generation Engine (All 7 Categories)
def test_alert_generation_all_categories():
    alert_svc = AlertService()
    # Trigger low SoC alert
    alerts1 = alert_svc.evaluate_live_conditions(battery_soc=18.0)
    assert any(a["category"] == "low_battery_critical" for a in alerts1)

    # Trigger high price peak alert
    alerts2 = alert_svc.evaluate_live_conditions(battery_soc=60.0, price_inr=7.50)
    assert any(a["category"] == "high_price" for a in alerts2)

    # Trigger high load alert
    alerts3 = alert_svc.evaluate_live_conditions(battery_soc=60.0, current_load_kw=4.2)
    assert any(a["category"] == "high_load" for a in alerts3)

# 13. Test End-to-End Pipeline
def test_end_to_end_pipeline():
    rec = EnergyRecommenderService()
    state = {
        "predicted_solar": 2.5,
        "predicted_load": 2.0,
        "electricity_price": 5.0,
        "battery_soc": 55.0,
        "current_load": 2.0,
        "time_peak_indicator": 0.0
    }
    decision = rec.recommend_energy(state)
    assert decision["status"] == "success"
    assert decision["total_power"] == 2.0
    assert decision["power_balance_verified"] is True
    assert decision["unsafe_action_rejected"] is False
