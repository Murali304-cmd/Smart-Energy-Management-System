import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from xai.xai_service import ExplainableAIService, explain_recommendation
from xai.explanation import validate_recommendation_input, validate_energy_balance, build_explanation
from xai.energy_explanation import explain_solar, explain_battery, explain_grid, explain_budget
from xai.decision_reason import generate_q_value_explanation, generate_user_friendly_explanation

def test_1_solar_only_explanation():
    rec_input = {
        "recommended_strategy": "SOLAR ONLY",
        "solar_power": 5.0,
        "battery_power": 0.0,
        "grid_power": 0.0,
        "total_power": 5.0,
        "predicted_solar": 6.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc_before": 70.0,
        "battery_soc_after": 75.0,
        "user_demand": 5.0,
        "user_budget": 100.0,
        "estimated_grid_cost": 0.0,
        "budget_status": "within_budget",
        "grid_usage": "none",
        "q_values": [12.5, 8.1, 2.0, 4.3]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert result["recommended_strategy"] == "SOLAR ONLY"
    assert "Solar was prioritized" in result["solar_explanation"]
    assert result["energy_contribution"]["solar_percentage"] == 100.0
    assert result["energy_contribution"]["grid_percentage"] == 0.0
    assert "no grid electricity was required" in result["grid_explanation"].lower()
    assert result["energy_balance_valid"] is True

def test_2_solar_plus_battery_explanation():
    rec_input = {
        "recommended_strategy": "SOLAR + BATTERY",
        "solar_power": 2.0,
        "battery_power": 3.0,
        "grid_power": 0.0,
        "total_power": 5.0,
        "predicted_solar": 2.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc_before": 80.0,
        "battery_soc_after": 50.0,
        "user_demand": 5.0,
        "user_budget": 100.0,
        "estimated_grid_cost": 0.0,
        "budget_status": "within_budget",
        "grid_usage": "none",
        "q_values": [8.5, 11.2, 3.0, 5.0]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert result["energy_allocation"]["solar_power"] == 2.0
    assert result["energy_allocation"]["battery_power"] == 3.0
    assert result["energy_allocation"]["grid_power"] == 0.0
    assert "battery supplied 3.00 kW" in result["battery_explanation"]
    assert "no grid electricity was required" in result["grid_explanation"].lower()
    assert result["energy_balance_valid"] is True

def test_3_solar_plus_battery_plus_grid_explanation():
    rec_input = {
        "recommended_strategy": "SOLAR + BATTERY + GRID",
        "solar_power": 4.0,
        "battery_power": 1.5,
        "grid_power": 0.5,
        "total_power": 6.0,
        "predicted_solar": 4.0,
        "predicted_load": 6.0,
        "predicted_price": 4.7,
        "battery_soc_before": 25.0,
        "battery_soc_after": 20.0,
        "user_demand": 6.0,
        "user_budget": 100.0,
        "estimated_grid_cost": 0.5875,
        "budget_status": "within_budget",
        "grid_usage": "minimal",
        "q_values": [10.2, 5.1, 2.0, 8.4]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert result["energy_allocation"]["solar_power"] == 4.0
    assert result["energy_allocation"]["battery_power"] == 1.5
    assert result["energy_allocation"]["grid_power"] == 0.5
    assert "Solar was prioritized" in result["solar_explanation"]
    assert "battery supplied 1.50 kW" in result["battery_explanation"]
    assert "grid supplied this remaining demand (0.50 kW)" in result["grid_explanation"]
    assert result["energy_contribution"]["grid_percentage"] == round((0.5 / 6.0) * 100, 2)
    assert result["energy_balance_valid"] is True

def test_4_battery_plus_grid_explanation():
    rec_input = {
        "recommended_strategy": "BATTERY + GRID",
        "solar_power": 0.0,
        "battery_power": 2.0,
        "grid_power": 3.0,
        "total_power": 5.0,
        "predicted_solar": 0.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc_before": 45.0,
        "battery_soc_after": 25.0,
        "user_demand": 5.0,
        "user_budget": 100.0,
        "estimated_grid_cost": 3.525,
        "budget_status": "within_budget",
        "grid_usage": "moderate",
        "q_values": [1.0, 9.5, 4.0, 2.0]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert result["energy_allocation"]["solar_power"] == 0.0
    assert result["energy_allocation"]["battery_power"] == 2.0
    assert result["energy_allocation"]["grid_power"] == 3.0
    assert "0.00 kW" in result["solar_explanation"]
    assert "battery supplied 2.00 kW" in result["battery_explanation"]
    assert "grid supplied this remaining demand (3.00 kW)" in result["grid_explanation"]

def test_5_grid_only_explanation():
    rec_input = {
        "recommended_strategy": "GRID BACKUP",
        "solar_power": 0.0,
        "battery_power": 0.0,
        "grid_power": 5.0,
        "total_power": 5.0,
        "predicted_solar": 0.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc_before": 15.0,
        "battery_soc_after": 15.0,
        "user_demand": 5.0,
        "user_budget": 100.0,
        "estimated_grid_cost": 5.875,
        "budget_status": "within_budget",
        "grid_usage": "heavy",
        "q_values": [-2.0, -1.0, 6.5, 1.0]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert result["energy_allocation"]["solar_power"] == 0.0
    assert result["energy_allocation"]["battery_power"] == 0.0
    assert result["energy_allocation"]["grid_power"] == 5.0
    assert "protecting battery health" in result["battery_explanation"]
    assert "grid supplied this remaining demand (5.00 kW)" in result["grid_explanation"]

def test_6_within_budget_explanation():
    rec_input = {
        "recommended_strategy": "SOLAR + BATTERY + GRID",
        "solar_power": 2.0,
        "battery_power": 1.0,
        "grid_power": 1.0,
        "total_power": 4.0,
        "predicted_solar": 2.0,
        "predicted_load": 4.0,
        "predicted_price": 5.0,
        "battery_soc_before": 30.0,
        "battery_soc_after": 20.0,
        "user_demand": 4.0,
        "user_budget": 50.0,
        "estimated_grid_cost": 1.25,
        "budget_status": "within_budget",
        "grid_usage": "minimal",
        "q_values": [5.0, 4.0, 3.0, 2.0]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert "within the user's configured budget" in result["budget_explanation"]

def test_7_over_budget_explanation():
    rec_input = {
        "recommended_strategy": "GRID BACKUP",
        "solar_power": 0.0,
        "battery_power": 0.0,
        "grid_power": 5.0,
        "total_power": 5.0,
        "predicted_solar": 0.0,
        "predicted_load": 5.0,
        "predicted_price": 6.0,
        "battery_soc_before": 15.0,
        "battery_soc_after": 15.0,
        "user_demand": 5.0,
        "user_budget": 2.0,
        "estimated_grid_cost": 7.5,
        "budget_status": "over_budget",
        "grid_usage": "heavy",
        "q_values": [1.0, 2.0, 3.0, 4.0]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert "exceeds the configured budget" in result["budget_explanation"]
    assert "insufficient to fully avoid additional grid usage" in result["budget_explanation"]

def test_8_invalid_energy_balance_flagged():
    rec_input = {
        "recommended_strategy": "SOLAR ONLY",
        "solar_power": 2.0,
        "battery_power": 1.0,
        "grid_power": 0.0,
        "total_power": 3.0,
        "predicted_solar": 2.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc_before": 50.0,
        "battery_soc_after": 40.0,
        "user_demand": 5.0,
        "user_budget": 100.0,
        "estimated_grid_cost": 0.0,
        "budget_status": "within_budget",
        "grid_usage": "none",
        "q_values": [5.0, 4.0, 3.0, 2.0]
    }
    result = explain_recommendation(rec_input)
    assert result["status"] == "success"
    assert result["energy_balance_valid"] is False
    assert "Energy allocation does not satisfy household demand" in result["message"]

def test_9_missing_battery_soc_returns_incomplete():
    incomplete_input = {
        "recommended_strategy": "SOLAR ONLY",
        "predicted_solar": 3.0,
        "predicted_load": 2.0,
        "predicted_price": 4.7
    }
    result = explain_recommendation(incomplete_input)
    assert result["status"] == "incomplete"
    assert "battery_soc" in result["missing_inputs"]
    assert "Unable to generate a complete explanation" in result["message"] or "is required" in result["message"]

def test_10_dqn_q_value_explanation_without_probabilities():
    q_vals = [14.25, 11.50, 4.10, 8.00]
    expl = generate_q_value_explanation(q_vals, 0, "SOLAR ONLY")
    assert expl["selected_q_value"] == 14.25
    assert expl["margin_over_second_best"] == 2.75
    assert "highest estimated decision value" in expl["explanation"]
    assert "%" not in expl["explanation"]
    assert "probability" not in expl["explanation"].lower()
    assert "saved" not in expl["explanation"].lower()

def test_technical_and_user_friendly_modes():
    rec_input = {
        "recommended_strategy": "SOLAR + BATTERY + GRID",
        "solar_power": 3.0,
        "battery_power": 1.5,
        "grid_power": 0.5,
        "total_power": 5.0,
        "predicted_solar": 3.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc_before": 50.0,
        "battery_soc_after": 35.0,
        "user_demand": 5.0,
        "user_budget": 100.0,
        "estimated_grid_cost": 0.5875,
        "budget_status": "within_budget",
        "grid_usage": "minimal",
        "q_values": [12.0, 9.0, 2.0, 5.0]
    }
    result = explain_recommendation(rec_input, explanation_level="technical")
    assert result["status"] == "success"
    assert "technical_explanation" in result
    assert "state_evaluated" in result["technical_explanation"]
    assert "soc_transition" in result["technical_explanation"]
    assert "user_friendly_explanation" in result
    assert "☀️ Solar:" in result["user_friendly_explanation"]
