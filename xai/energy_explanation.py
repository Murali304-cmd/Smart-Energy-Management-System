from typing import Dict, Any, Tuple, Optional

def explain_solar(
    solar_power: float,
    predicted_solar: float,
    user_demand: float
) -> str:
    if solar_power > 0.0:
        if solar_power >= user_demand:
            return (
                f"Solar was prioritized because renewable generation ({predicted_solar:.2f} kW) was available. "
                f"It fully supplied {solar_power:.2f} kW of the {user_demand:.2f} kW household demand with zero grid dependency."
            )
        else:
            return (
                f"Solar was prioritized because renewable generation ({predicted_solar:.2f} kW) was available. "
                f"It supplied {solar_power:.2f} kW towards the {user_demand:.2f} kW household demand."
            )
    else:
        if predicted_solar <= 0.05:
            return "Solar power did not contribute because available solar generation was 0.00 kW."
        else:
            return f"Solar generation was {predicted_solar:.2f} kW, but could not contribute directly to household load."

def explain_battery(
    battery_power: float,
    battery_soc_before: float,
    battery_soc_after: float,
    user_demand: float,
    solar_power: float,
    min_soc: float = 20.0
) -> str:
    rem_after_solar = max(0.0, user_demand - solar_power)
    if battery_power > 0.0:
        return (
            f"Solar could not fully satisfy the demand, so the battery supplied {battery_power:.2f} kW "
            f"for the remaining {rem_after_solar:.2f} kW requirement. "
            f"Battery SOC changed from {battery_soc_before:.1f}% to {battery_soc_after:.1f}%."
        )
    else:
        if rem_after_solar <= 0.001:
            return "Battery was not required because Solar supplied the required demand."
        elif battery_soc_before <= min_soc:
            return (
                f"Battery did not discharge because current SOC ({battery_soc_before:.1f}%) is at or below "
                f"the minimum reserve limit ({min_soc:.1f}%), protecting battery health."
            )
        else:
            return f"Battery discharge was not dispatched (SOC remained at {battery_soc_before:.1f}%)."

def explain_grid(
    grid_power: float,
    user_demand: float,
    solar_power: float,
    battery_power: float,
    estimated_grid_cost: float,
    predicted_price: float
) -> str:
    clean_supplied = solar_power + battery_power
    rem_unmet = max(0.0, user_demand - clean_supplied)
    if grid_power > 0.0:
        return (
            f"After Solar and Battery supplied {clean_supplied:.2f} kW, {rem_unmet:.2f} kW remained. "
            f"The grid supplied this remaining demand ({grid_power:.2f} kW) as backup at ₹{predicted_price:.2f}/kWh "
            f"(estimated cost: ₹{estimated_grid_cost:.2f})."
        )
    else:
        return "Solar and Battery were sufficient to satisfy the household demand, so no grid electricity was required."

def calculate_energy_contributions(
    solar_power: float,
    battery_power: float,
    grid_power: float,
    user_demand: float
) -> Dict[str, float]:
    demand = max(0.01, user_demand)
    solar_to_load = min(max(0.0, solar_power), demand)
    batt_to_load = min(max(0.0, battery_power), max(0.0, demand - solar_to_load))
    grid_to_load = max(0.0, demand - solar_to_load - batt_to_load)

    solar_pct = round((solar_to_load / demand) * 100.0, 2)
    batt_pct = round((batt_to_load / demand) * 100.0, 2)
    grid_pct = round(max(0.0, 100.0 - solar_pct - batt_pct), 2)
    return {
        "solar_percentage": solar_pct,
        "battery_percentage": batt_pct,
        "grid_percentage": grid_pct
    }

def explain_budget(
    user_budget: float,
    estimated_grid_cost: float,
    budget_status: str
) -> str:
    if budget_status == "within_budget" or estimated_grid_cost <= user_budget:
        return (
            f"Estimated grid cost (₹{estimated_grid_cost:.2f}) is within the user's configured budget "
            f"(₹{user_budget:.2f})."
        )
    else:
        return (
            f"Estimated cost (₹{estimated_grid_cost:.2f}) exceeds the configured budget (₹{user_budget:.2f}). "
            f"The system attempted to minimize grid usage, but the available Solar and Battery energy "
            f"were insufficient to fully avoid additional grid usage."
        )
