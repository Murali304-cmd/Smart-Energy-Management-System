import math
from typing import Dict, Any, List, Tuple, Optional, Union
from xai.energy_explanation import (
    explain_solar,
    explain_battery,
    explain_grid,
    calculate_energy_contributions,
    explain_budget
)
from xai.decision_reason import (
    generate_decision_summary,
    generate_q_value_explanation,
    generate_key_factors,
    generate_feature_contributions,
    generate_user_friendly_explanation,
    generate_technical_explanation
)

analyze_factor_contributions = generate_feature_contributions

REQUIRED_INPUT_FIELDS = [
    "user_demand",
    "battery_soc",
    "predicted_price"
]

def validate_recommendation_input(data: Any) -> Tuple[bool, List[str], Optional[str]]:
    if not isinstance(data, dict):
        return False, ["input_type"], f"Expected dict input, got {type(data).__name__}."

    missing = []
    
    # Check battery SOC (supports 'battery_soc' or 'battery_soc_before')
    bat_soc = data.get("battery_soc", data.get("battery_soc_before"))
    if bat_soc is None:
        missing.append("battery_soc")

    # Check predictions
    if "predicted_solar" not in data or data["predicted_solar"] is None:
        missing.append("predicted_solar")
    if "predicted_load" not in data or data["predicted_load"] is None:
        missing.append("predicted_load")
    if "predicted_price" not in data or data["predicted_price"] is None:
        missing.append("predicted_price")

    # Check demand
    demand = data.get("user_demand", data.get("predicted_load"))
    if demand is None:
        missing.append("user_demand")

    if missing:
        missing_str = ", ".join(missing)
        return False, missing, f"{missing_str} is required to generate the recommendation explanation."

    # Numeric validation
    for k in ["predicted_solar", "predicted_load", "predicted_price"]:
        try:
            val = float(data[k])
            if math.isnan(val) or val < 0.0:
                missing.append(k)
        except (ValueError, TypeError):
            missing.append(k)

    try:
        val_soc = float(bat_soc)
        if math.isnan(val_soc) or not (0.0 <= val_soc <= 100.0):
            missing.append("battery_soc")
    except (ValueError, TypeError):
        missing.append("battery_soc")

    if "action_id" in data and data["action_id"] is not None:
        try:
            act = int(data["action_id"])
            if act not in [0, 1, 2, 3]:
                missing.append("action_id")
        except (ValueError, TypeError):
            missing.append("action_id")

    if missing:
        return False, missing, f"Invalid or non-numeric values detected in: {', '.join(set(missing))}."

    return True, [], None

def validate_energy_balance(
    solar_power: float,
    battery_power: float,
    grid_power: float,
    user_demand: float,
    tolerance: float = 1e-3
) -> Tuple[bool, Optional[str]]:
    total = solar_power + battery_power + grid_power
    diff = abs(total - user_demand)
    if diff <= tolerance:
        return True, None
    else:
        return False, f"Energy allocation does not satisfy household demand (Total: {total:.2f} kW != Demand: {user_demand:.2f} kW)."

def build_explanation(
    recommendation_data: Dict[str, Any],
    explanation_level: str = "simple"
) -> Dict[str, Any]:
    valid, missing, err_msg = validate_recommendation_input(recommendation_data)
    if not valid:
        return {
            "status": "incomplete",
            "missing_inputs": missing,
            "message": err_msg or "Unable to generate a complete explanation."
        }

    # Extract clean parameters
    pred_solar = float(recommendation_data.get("predicted_solar", recommendation_data.get("solar_power_kw", 0.0)))
    pred_load = float(recommendation_data.get("predicted_load", recommendation_data.get("household_load_kw", 0.0)))
    pred_price = float(recommendation_data.get("predicted_price", recommendation_data.get("predicted_price_inr", 4.70)))
    bat_soc_before = float(recommendation_data.get("battery_soc_before", recommendation_data.get("battery_soc", 50.0)))
    bat_soc_after = float(recommendation_data.get("battery_soc_after", bat_soc_before))
    user_demand = float(recommendation_data.get("user_demand", recommendation_data.get("household_load_kw", pred_load)))
    user_budget = float(recommendation_data.get("user_budget", 100.0))

    solar_power = float(recommendation_data.get("solar_power", recommendation_data.get("solar_power_kw", min(pred_solar, user_demand))))
    battery_power = float(recommendation_data.get("battery_power", recommendation_data.get("battery_power_kw", 0.0)))
    grid_power = float(recommendation_data.get("grid_power", recommendation_data.get("grid_power_kw", max(0.0, user_demand - solar_power - battery_power))))
    total_power = float(recommendation_data.get("total_power", solar_power + battery_power + grid_power))

    strategy = recommendation_data.get("energy_strategy", recommendation_data.get("recommended_strategy", recommendation_data.get("recommended_source", "HYBRID")))
    action_id = int(recommendation_data.get("action_id", recommendation_data.get("dqn_action_id", 0)))
    q_values = recommendation_data.get("q_values", [0.0, 0.0, 0.0, 0.0])

    estimated_grid_cost = float(recommendation_data.get("estimated_grid_cost", recommendation_data.get("estimated_cost", round(grid_power * 0.25 * pred_price, 4))))
    budget_status = recommendation_data.get("budget_status", "within_budget" if estimated_grid_cost <= user_budget else "over_budget")

    # Energy balance check
    balance_valid, balance_msg = validate_energy_balance(solar_power, battery_power, grid_power, user_demand)

    # Explanations
    solar_expl = explain_solar(solar_power, pred_solar, user_demand)
    battery_expl = explain_battery(battery_power, bat_soc_before, bat_soc_after, user_demand, solar_power)
    grid_expl = explain_grid(grid_power, user_demand, solar_power, battery_power, estimated_grid_cost, pred_price)
    budget_expl = explain_budget(user_budget, estimated_grid_cost, budget_status)
    q_val_expl = generate_q_value_explanation(q_values, action_id, strategy)

    contributions = calculate_energy_contributions(solar_power, battery_power, grid_power, user_demand)
    key_factors = generate_key_factors(pred_solar, pred_load, pred_price, bat_soc_before, user_budget)
    feat_contribs = generate_feature_contributions(
        pred_solar, pred_load, pred_price, bat_soc_before, user_budget,
        solar_power, battery_power, grid_power
    )
    decision_summary = generate_decision_summary(
        strategy, solar_power, battery_power, grid_power, user_demand, budget_status, estimated_grid_cost
    )
    user_friendly_text = generate_user_friendly_explanation(
        strategy, solar_power, battery_power, grid_power, user_demand, budget_status, estimated_grid_cost, user_budget
    )

    result = {
        "status": "success",
        "recommended_strategy": strategy,
        "recommended_source": strategy,
        "decision_summary": decision_summary,
        "energy_allocation": {
            "solar_power": round(solar_power, 3),
            "battery_power": round(battery_power, 3),
            "grid_power": round(grid_power, 3),
            "total_power": round(total_power, 3)
        },
        "energy_contribution": contributions,
        "key_factors": key_factors,
        "feature_contributions": feat_contribs,
        "solar_explanation": solar_expl,
        "battery_explanation": battery_expl,
        "grid_explanation": grid_expl,
        "budget_explanation": budget_expl,
        "q_value_explanation": q_val_expl["explanation"],
        "q_value_summary": q_val_expl,
        "user_friendly_explanation": user_friendly_text,
        "energy_balance_valid": balance_valid
    }

    if not balance_valid and balance_msg:
        result["message"] = balance_msg

    if explanation_level == "technical":
        state_vec = [pred_solar, pred_load, pred_price, bat_soc_before, user_demand, user_budget]
        result["technical_explanation"] = generate_technical_explanation(
            state_vector=state_vec,
            q_values=q_values,
            action_id=action_id,
            strategy=strategy,
            energy_allocation=result["energy_allocation"],
            battery_soc_before=bat_soc_before,
            battery_soc_after=bat_soc_after,
            energy_balance_valid=balance_valid
        )

    return result
