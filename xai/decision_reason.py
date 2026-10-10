from typing import Dict, Any, List, Tuple, Optional

def generate_decision_summary(
    strategy: str,
    solar_power: float,
    battery_power: float,
    grid_power: float,
    user_demand: float,
    budget_status: str,
    estimated_grid_cost: float
) -> str:
    parts = []
    if solar_power > 0.0 and solar_power >= user_demand:
        parts.append("Solar generation fully supplied the household demand")
    elif solar_power > 0.0:
        parts.append(f"Solar supplied {solar_power:.2f} kW of the demand")
    
    if battery_power > 0.0:
        if solar_power >= user_demand or strategy == "SOLAR ONLY":
            parts.append(f"surplus solar ({battery_power:.2f} kW) charged the battery")
        else:
            parts.append(f"the battery supplied {battery_power:.2f} kW for the remaining demand")
    
    if grid_power > 0.0:
        parts.append(f"grid usage was limited to the final {grid_power:.2f} kW backup")
    elif solar_power + battery_power >= user_demand or solar_power >= user_demand:
        parts.append("zero grid power was needed")

    is_within = (
        budget_status in ("within_budget", "Within Budget")
        or str(budget_status).lower().replace(" ", "_") == "within_budget"
        or estimated_grid_cost <= 0.0
    )
    budget_text = (
        "The estimated cost remained within the configured budget."
        if is_within
        else f"Estimated cost (₹{estimated_grid_cost:.2f}) exceeded the target budget."
    )

    if parts:
        summary_core = ", ".join(parts).capitalize() + "."
    else:
        summary_core = f"Energy demand of {user_demand:.2f} kW was met using {strategy}."

    return f"{summary_core} {budget_text}"

def generate_q_value_explanation(
    q_values: List[float],
    action_id: int,
    strategy_name: str
) -> Dict[str, Any]:
    if not q_values:
        return {
            "selected_action": strategy_name,
            "selected_q_value": 0.0,
            "margin_over_second_best": 0.0,
            "explanation": "No Q-values available."
        }

    q_vals = [float(q) for q in q_values]
    max_idx = int(max(range(len(q_vals)), key=lambda i: q_vals[i]))
    selected_val = q_vals[action_id] if 0 <= action_id < len(q_vals) else q_vals[max_idx]

    sorted_q = sorted(q_vals, reverse=True)
    margin = round(sorted_q[0] - sorted_q[1], 4) if len(sorted_q) > 1 else 0.0

    if margin < 0.2 and len(sorted_q) > 1:
        expl = (
            f"The DQN evaluated very close valuations between the top strategies "
            f"(selected Q-value: {selected_val:.2f}, margin: {margin:.2f})."
        )
    else:
        expl = (
            f"The DQN assigned the highest estimated decision value ({selected_val:.2f}) "
            f"to the selected energy strategy ({strategy_name}) with a confidence margin of {margin:.2f}."
        )

    return {
        "selected_action": strategy_name,
        "action_id": action_id,
        "selected_q_value": round(selected_val, 4),
        "margin_over_second_best": margin,
        "all_q_values": [round(q, 4) for q in q_vals],
        "explanation": expl
    }

def generate_key_factors(
    predicted_solar: float,
    predicted_load: float,
    predicted_price: float,
    battery_soc: float,
    user_budget: float
) -> List[str]:
    factors = [
        f"Predicted solar generation ({predicted_solar:.2f} kW)",
        f"Predicted household demand ({predicted_load:.2f} kW)",
        f"Battery SOC ({battery_soc:.1f}%)",
        f"Predicted electricity cost (₹{predicted_price:.2f}/kWh)",
        f"User budget (₹{user_budget:.2f})"
    ]
    return factors

def generate_feature_contributions(
    predicted_solar: float,
    predicted_load: float,
    predicted_price: float,
    battery_soc: float,
    user_budget: float,
    solar_power: float,
    battery_power: float,
    grid_power: float
) -> Dict[str, Dict[str, Any]]:
    solar_role = "high solar availability supports clean self-consumption" if solar_power > 0.5 else "low or zero solar generation"
    load_role = f"determines required household energy ({predicted_load:.2f} kW)"
    bat_role = "provides discharge energy" if battery_power > 0 else ("preserves reserve capacity" if battery_soc <= 20.0 else "sufficient reserve ready")
    price_role = "affects grid electricity cost" if grid_power > 0 else "grid avoided to minimize tariff expense"
    budget_role = "guides maximum acceptable grid energy cost"

    return {
        "predicted_solar": {
            "value": round(predicted_solar, 2),
            "unit": "kW",
            "role": solar_role
        },
        "predicted_load": {
            "value": round(predicted_load, 2),
            "unit": "kW",
            "role": load_role
        },
        "battery_soc": {
            "value": round(battery_soc, 1),
            "unit": "%",
            "role": bat_role
        },
        "predicted_price": {
            "value": round(predicted_price, 2),
            "unit": "₹/kWh",
            "role": price_role
        },
        "user_budget": {
            "value": round(user_budget, 2),
            "unit": "₹",
            "role": budget_role
        }
    }

def generate_user_friendly_explanation(
    strategy: str,
    solar_power: float,
    battery_power: float,
    grid_power: float,
    user_demand: float,
    budget_status: str,
    estimated_grid_cost: float,
    user_budget: float
) -> str:
    lines = [
        "⚡ Energy Recommendation Breakdown",
        "",
        f"☀️ Solar:   {solar_power:.2f} kW",
        f"🔋 Battery: {battery_power:.2f} kW",
        f"⚡ Grid:    {grid_power:.2f} kW",
        "",
        "Why?",
        ""
    ]
    if solar_power >= user_demand and user_demand > 0.0:
        lines.append("• Solar supplied 100% of your household demand from clean renewable energy.")
    elif solar_power > 0.0:
        lines.append(f"• Solar covered {solar_power:.2f} kW of the demand directly.")
    
    if battery_power > 0.0:
        lines.append(f"• The battery discharged {battery_power:.2f} kW to cover the remaining requirement.")
    
    if grid_power > 0.0:
        lines.append(f"• Only {grid_power:.2f} kW was drawn from the grid as backup.")
    elif solar_power + battery_power >= user_demand:
        lines.append("• Zero grid power was imported.")

    lines.append("")
    lines.append("💰 Budget:")
    is_within_expl = (
        budget_status in ("within_budget", "Within Budget")
        or str(budget_status).lower().replace(" ", "_") == "within_budget"
        or estimated_grid_cost <= 0.0
    )
    if is_within_expl:
        lines.append(f"• Estimated grid cost (₹{estimated_grid_cost:.2f}) is within your configured budget (₹{user_budget:.2f}).")
    else:
        lines.append(f"• Estimated grid cost (₹{estimated_grid_cost:.2f}) exceeds your target budget (₹{user_budget:.2f}).")

    return "\n".join(lines)

def generate_technical_explanation(
    state_vector: List[float],
    q_values: List[float],
    action_id: int,
    strategy: str,
    energy_allocation: Dict[str, float],
    battery_soc_before: float,
    battery_soc_after: float,
    energy_balance_valid: bool
) -> Dict[str, Any]:
    return {
        "state_evaluated": state_vector,
        "state_feature_names": [
            "predicted_solar",
            "predicted_load",
            "predicted_price",
            "battery_soc",
            "user_demand",
            "user_budget"
        ],
        "q_values": q_values,
        "action_id": action_id,
        "selected_strategy": strategy,
        "energy_allocation": energy_allocation,
        "soc_transition": {
            "soc_before": battery_soc_before,
            "soc_after": battery_soc_after,
            "delta_soc": round(battery_soc_after - battery_soc_before, 2)
        },
        "energy_balance_verified": energy_balance_valid
    }
