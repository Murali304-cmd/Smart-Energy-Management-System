from typing import Dict, Any, Tuple, Optional, List, Union
import numpy as np
from recommendation.allocation import BatteryConfig, allocate_energy

try:
    from config.settings import (
        BATTERY_CAPACITY_KWH,
        BATTERY_MIN_SOC,
        BATTERY_MAX_SOC,
        BATTERY_DISCHARGE_EFFICIENCY,
        BATTERY_CHARGE_EFFICIENCY,
        BATTERY_MAX_DISCHARGE_KW,
        BATTERY_MAX_CHARGE_KW
    )
except ImportError:
    BATTERY_CAPACITY_KWH = 20.0
    BATTERY_MIN_SOC = 20.0
    BATTERY_MAX_SOC = 100.0
    BATTERY_DISCHARGE_EFFICIENCY = 0.95
    BATTERY_CHARGE_EFFICIENCY = 0.95
    BATTERY_MAX_DISCHARGE_KW = 10.0
    BATTERY_MAX_CHARGE_KW = 6.0

# Redesigned 4-Action Space (Goal 4)
ACTION_SOLAR_PRIORITY = 0       # "SOLAR_PRIORITY"
ACTION_BATTERY_DISPATCH = 1     # "BATTERY_DISPATCH"
ACTION_GRID_USAGE = 2           # "GRID_USAGE"
ACTION_PEAK_SHAVING = 3         # "PEAK_SHAVING"

# Aliases for backwards compatibility
ACTION_PRIORITY_HYBRID = ACTION_SOLAR_PRIORITY
ACTION_BATTERY_CONSERVATION = ACTION_BATTERY_DISPATCH
ACTION_GRID_MINIMIZE = ACTION_GRID_USAGE
ACTION_SOLAR = ACTION_SOLAR_PRIORITY
ACTION_BATTERY = ACTION_BATTERY_DISPATCH
ACTION_GRID = ACTION_GRID_USAGE

ACTION_NAMES = {
    ACTION_SOLAR_PRIORITY: "SOLAR_PRIORITY",
    ACTION_BATTERY_DISPATCH: "BATTERY_DISPATCH",
    ACTION_GRID_USAGE: "GRID_USAGE",
    ACTION_PEAK_SHAVING: "PEAK_SHAVING"
}

STATE_DIM = 6
ACTION_DIM = 4

# Redesigned 6D State Vector (Goal 4):
# [solar prediction, load prediction, electricity price, battery SoC, current load, time/peak indicator]
STATE_FEATURES = [
    "predicted_solar",
    "predicted_load",
    "electricity_price",
    "battery_soc",
    "current_load",
    "time_peak_indicator"
]

def calculate_reward(
    state: np.ndarray,
    action: int,
    next_state: np.ndarray,
    info: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Explicit Multi-Objective Physical Reward Function (Goal 5):
    + lower electricity cost (relative to grid-only baseline)
    + higher solar utilization (self-consumption & green battery charging)
    + maintaining strict power balance (P_solar + P_battery + P_grid == P_demand)
    + appropriate battery usage (healthy cycling within 30% - 85% SoC)
    - unnecessary grid usage when clean power is available
    - battery SoC below safe limit (20%)
    - battery overcharge (> 100%)
    - unnecessary peak demand during high tariff hours
    - unsafe action rejection
    """
    solar_power = float(info.get("solar_power", 0.0))
    battery_power = float(info.get("battery_power", 0.0))
    grid_power = float(info.get("grid_power", 0.0))
    current_load = max(0.1, float(state[4]) if len(state) > 4 else float(state[1]))
    price = max(0.1, float(state[2]))
    is_peak = float(state[5]) if len(state) > 5 else 0.0
    next_soc = float(next_state[3])
    cost_savings = float(info.get("cost_savings_inr", 0.0))
    baseline_cost = float(info.get("baseline_grid_cost", current_load * 0.25 * price))
    battery_charged = float(info.get("battery_charged_kwh", 0.0))
    balance_error = float(info.get("balance_error_kw", 0.0))
    unsafe_rejected = bool(info.get("unsafe_action_rejected", False))
    pred_solar = float(state[0])

    # 1. Lower electricity cost reward
    r_cost = 2.5 * (cost_savings / max(0.01, baseline_cost))

    # 2. Solar utilization reward
    solar_utilized = solar_power + (battery_charged / 0.25)
    r_solar = 1.8 * (solar_utilized / max(0.1, pred_solar)) if pred_solar > 0.1 else 0.5

    # 3. Power balance maintenance (+0.5 if satisfied, heavy penalty if imbalanced)
    r_balance = 0.5 if balance_error < 1e-4 else -10.0 * balance_error

    # 4. Appropriate battery usage reward (healthy cycling 30% - 85%)
    r_soc_health = 0.4 if (30.0 <= next_soc <= 85.0) else 0.0

    # 5. Penalize unnecessary grid usage (if battery has ample SoC > 40% and it is not an off-peak grid action)
    p_unnecessary_grid = 0.0
    if grid_power > 0.1 and next_soc > 40.0 and action != ACTION_GRID_USAGE and not (is_peak > 0.5):
        p_unnecessary_grid = -1.5 * (grid_power / current_load)

    # 6. Penalize battery SoC below safe limit (20%)
    p_low_soc = -6.0 if next_soc < BATTERY_MIN_SOC else (-1.0 if next_soc < 25.0 else 0.0)

    # 7. Penalize battery overcharge (> 100%)
    p_overcharge = -6.0 if next_soc > BATTERY_MAX_SOC else 0.0

    # 8. Penalize unnecessary peak demand during peak tariff hours
    p_peak_grid = -3.0 * (grid_power / current_load) if (is_peak > 0.5 and grid_power > 0.2) else 0.0

    # 9. Penalize unsafe action attempts (attempting to discharge below 20% or charge above 100%)
    p_unsafe = -3.0 if unsafe_rejected else 0.0

    total_reward = (
        r_cost
        + r_solar
        + r_balance
        + r_soc_health
        + p_unnecessary_grid
        + p_low_soc
        + p_overcharge
        + p_peak_grid
        + p_unsafe
    )

    info["reward_components"] = {
        "r_cost": round(r_cost, 4),
        "r_solar": round(r_solar, 4),
        "r_balance": round(r_balance, 4),
        "r_soc_health": round(r_soc_health, 4),
        "p_unnecessary_grid": round(p_unnecessary_grid, 4),
        "p_low_soc": round(p_low_soc, 4),
        "p_overcharge": round(p_overcharge, 4),
        "p_peak_grid": round(p_peak_grid, 4),
        "p_unsafe": round(p_unsafe, 4),
        "total_reward": round(total_reward, 4)
    }

    return round(total_reward, 4)

class EnergyManagementEnv:
    def __init__(
        self,
        dt_hours: float = 0.25,
        battery_config: Optional[BatteryConfig] = None
    ):
        self.dt_hours = dt_hours
        self.battery_config = battery_config or BatteryConfig(dt_hours=dt_hours)
        self.state: Optional[np.ndarray] = None
        self.current_step = 0

    def reset(self, initial_state: Optional[Union[np.ndarray, List[float], Dict[str, float]]] = None) -> np.ndarray:
        self.current_step = 0
        if initial_state is not None:
            if isinstance(initial_state, dict):
                pred_load = float(initial_state.get("predicted_load", 2.0))
                curr_load = float(initial_state.get("current_load", pred_load))
                self.state = np.array([
                    float(initial_state.get("predicted_solar", 0.0)),
                    pred_load,
                    float(initial_state.get("electricity_price", 4.7)),
                    float(initial_state.get("battery_soc", 60.0)),
                    curr_load,
                    float(initial_state.get("time_peak_indicator", 0.0))
                ], dtype=np.float32)
            else:
                arr = list(initial_state)
                while len(arr) < 6:
                    arr.append(0.0)
                self.state = np.array(arr[:6], dtype=np.float32)
        else:
            self.state = np.array([2.5, 1.8, 4.7, 70.0, 1.8, 0.0], dtype=np.float32)
        return self.state.copy()

    def step(
        self,
        action: int,
        next_predicted_state: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        if self.state is None:
            raise RuntimeError("Environment must be reset before calling step().")

        pred_solar = float(self.state[0])
        pred_load = float(self.state[1])
        curr_price = float(self.state[2])
        curr_soc = float(self.state[3])
        curr_load = float(self.state[4])
        is_peak = float(self.state[5])

        alloc = allocate_energy(
            predicted_solar=pred_solar,
            battery_soc=curr_soc,
            user_demand=curr_load,
            user_budget=100.0,
            predicted_price=curr_price,
            action=action,
            battery_config=self.battery_config
        )

        new_soc = alloc["battery_soc_after"]

        if next_predicted_state is not None:
            n_arr = list(next_predicted_state)
            next_solar = float(n_arr[0])
            next_load = float(n_arr[1])
            next_price = float(n_arr[2])
            next_curr_load = float(n_arr[4]) if len(n_arr) > 4 else next_load
            next_is_peak = float(n_arr[5]) if len(n_arr) > 5 else 0.0
            next_state = np.array([next_solar, next_load, next_price, new_soc, next_curr_load, next_is_peak], dtype=np.float32)
        else:
            next_state = np.array([pred_solar, pred_load, curr_price, new_soc, curr_load, is_peak], dtype=np.float32)

        info = {
            "action": action,
            "action_name": ACTION_NAMES.get(action, "UNKNOWN"),
            **alloc,
            "solar_supplied_kw": alloc["solar_power"],
            "battery_supplied_kw": alloc["battery_power"],
            "grid_supplied_kw": alloc["grid_power"],
            "new_soc": new_soc
        }

        reward = calculate_reward(self.state, action, next_state, info)
        info["reward"] = reward

        self.state = next_state
        self.current_step += 1
        done = False
        return (next_state, reward, done, info)
