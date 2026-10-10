import os
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np

try:
    from config.settings import DQN_MODEL_PATH, BATTERY_MIN_SOC, BATTERY_MAX_SOC, BATTERY_CAPACITY_KWH
except ImportError:
    DQN_MODEL_PATH = Path(__file__).resolve().parent.parent / "trained_models" / "dqn_energy_recommender.pth"
    BATTERY_MIN_SOC = 20.0
    BATTERY_MAX_SOC = 100.0
    BATTERY_CAPACITY_KWH = 20.0

from recommendation.environment import (
    STATE_DIM,
    ACTION_DIM,
    ACTION_NAMES,
    ACTION_PRIORITY_HYBRID
)
from recommendation.allocation import BatteryConfig, allocate_energy
from recommendation.dqn_model import DQNAgent, StateScaler

logger = logging.getLogger("SEMS.Recommender")

class EnergyRecommenderService:
    def __init__(self, model_path: Path = DQN_MODEL_PATH, battery_config: Optional[BatteryConfig] = None):
        self.model_path = Path(model_path)
        self.battery_config = battery_config or BatteryConfig()
        self.agent: Optional[DQNAgent] = None
        self._load_agent()

    def _load_agent(self):
        scaler_path = self.model_path.parent / "dqn_scaler_config.json"
        scaler = StateScaler.load_config(scaler_path) if scaler_path.exists() else StateScaler()
        self.agent = DQNAgent(state_dim=STATE_DIM, action_dim=ACTION_DIM, scaler=scaler)
        if self.model_path.exists():
            try:
                self.agent.load(self.model_path)
                logger.info("Trained DQN model loaded successfully into Recommender Service.")
            except Exception as e:
                logger.warning(f"Could not load DQN model from {self.model_path}: {e}")
        else:
            logger.warning(f"DQN model weights not found at {self.model_path}. Train the model using train_dqn.py.")

    def _validate_inputs(self, state_input: Union[Dict[str, Any], List[float], np.ndarray]) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, Any]]]:
        if isinstance(state_input, dict):
            try:
                pred_solar = float(state_input.get("predicted_solar", 0.0))
                pred_load = float(state_input.get("predicted_load", 1.5))
                pred_price = float(state_input.get("electricity_price", state_input.get("predicted_price", 4.70)))
                bat_soc = float(state_input.get("battery_soc", 50.0))
                curr_load = float(state_input.get("current_load", state_input.get("user_demand", pred_load)))
                is_peak = float(state_input.get("time_peak_indicator", state_input.get("is_peak", 0.0)))
            except (ValueError, TypeError) as e:
                return None, {"status": "error", "error": f"Invalid numeric format in state inputs: {e}"}
        elif isinstance(state_input, (list, tuple, np.ndarray)):
            if len(state_input) < 4:
                return None, {"status": "error", "error": f"Expected at least 4 state values, got {len(state_input)}."}
            try:
                pred_solar = float(state_input[0])
                pred_load = float(state_input[1])
                pred_price = float(state_input[2])
                bat_soc = float(state_input[3])
                curr_load = float(state_input[4]) if len(state_input) > 4 else pred_load
                is_peak = float(state_input[5]) if len(state_input) > 5 else 0.0
            except (ValueError, TypeError) as e:
                return None, {"status": "error", "error": f"Invalid numeric format: {e}"}
        else:
            return None, {"status": "error", "error": "Expected dict or list for state_input."}

        # Physical clamping & validations
        pred_solar = max(0.0, pred_solar)
        pred_load = max(0.05, pred_load)
        pred_price = max(0.0, pred_price)
        bat_soc = max(0.0, min(100.0, bat_soc))
        curr_load = max(0.05, curr_load)
        is_peak = 1.0 if is_peak > 0.5 else 0.0

        return {
            "predicted_solar": pred_solar,
            "predicted_load": pred_load,
            "electricity_price": pred_price,
            "battery_soc": bat_soc,
            "current_load": curr_load,
            "time_peak_indicator": is_peak
        }, None

    def generate_xai_explanation(
        self,
        action_name: str,
        pred_solar: float,
        pred_load: float,
        battery_soc: float,
        price: float,
        current_load: float,
        is_peak: float
    ) -> Dict[str, Any]:
        """
        Provides simple, transparent XAI explanation per Goal 10.
        """
        reasons = [
            f"Predicted solar = {pred_solar:.2f} kW",
            f"Predicted load = {pred_load:.2f} kW (Current load = {current_load:.2f} kW)",
            f"Battery SoC = {battery_soc:.1f}%",
            f"Grid price = ₹{price:.2f}/unit ({'Peak tariff slot' if is_peak > 0.5 else 'Normal off-peak rate'})"
        ]

        if action_name == "SOLAR_PRIORITY":
            if pred_solar >= current_load:
                explanation = "Solar priority was selected because available solar generation is sufficient to meet current demand without grid import."
            else:
                explanation = "Solar priority was selected to maximize clean self-consumption; available solar is used first and battery covers the deficit."
        elif action_name == "PEAK_SHAVING":
            explanation = "Peak shaving was activated due to high electricity tariff; battery discharges to eliminate expensive peak grid demand."
        elif action_name == "BATTERY_DISPATCH":
            explanation = "Battery conservation was selected to preserve energy storage capacity for upcoming peak demand intervals."
        elif action_name == "GRID_USAGE":
            explanation = "Grid usage was selected because current electricity tariff is low, or battery SoC is near the 20% safety cutoff."
        else:
            explanation = f"{action_name} dispatched according to optimal cost and physical power balance constraints."

        return {
            "decision": action_name,
            "reasons": reasons,
            "explanation": explanation
        }

    def recommend_energy(self, state_input: Union[Dict[str, Any], List[float], np.ndarray]) -> Dict[str, Any]:
        valid_vals, err_dict = self._validate_inputs(state_input)
        if err_dict is not None:
            return err_dict

        pred_solar = valid_vals["predicted_solar"]
        pred_load = valid_vals["predicted_load"]
        pred_price = valid_vals["electricity_price"]
        bat_soc = valid_vals["battery_soc"]
        curr_load = valid_vals["current_load"]
        is_peak = valid_vals["time_peak_indicator"]

        # 6D state vector for DQN agent
        state_vector = [pred_solar, pred_load, pred_price, bat_soc, curr_load, is_peak]

        if self.agent is not None and self.agent.is_trained:
            action_id, q_values = self.agent.select_action(state_vector, eval_mode=True)
        else:
            # Rule fallback
            if pred_solar >= curr_load:
                action_id = 0 # SOLAR_PRIORITY
            elif is_peak > 0.5 and bat_soc > 25.0:
                action_id = 3 # PEAK_SHAVING
            elif bat_soc > 30.0:
                action_id = 0 # SOLAR_PRIORITY
            else:
                action_id = 2 # GRID_USAGE
            q_values = [5.0, 3.0, 2.0, 4.0]

        alloc = allocate_energy(
            predicted_solar=pred_solar,
            battery_soc=bat_soc,
            user_demand=curr_load,
            user_budget=100.0,
            predicted_price=pred_price,
            action=action_id,
            battery_config=self.battery_config
        )

        xai = self.generate_xai_explanation(
            action_name=alloc["recommended_strategy"],
            pred_solar=pred_solar,
            pred_load=pred_load,
            battery_soc=bat_soc,
            price=pred_price,
            current_load=curr_load,
            is_peak=is_peak
        )

        return {
            "status": "success",
            "decision": alloc["recommended_strategy"],
            "recommended_strategy": alloc["recommended_strategy"],
            "action_id": action_id,
            "solar_power": alloc["solar_power"],
            "battery_power": alloc["battery_power"],
            "grid_power": alloc["grid_power"],
            "total_power": alloc["total_power"],
            "surplus_solar": alloc["surplus_solar"],
            "export_power": alloc["export_power"],
            "export_credit_inr": alloc["export_credit_inr"],
            "predicted_solar": pred_solar,
            "predicted_load": pred_load,
            "electricity_price": pred_price,
            "battery_soc_before": alloc["battery_soc_before"],
            "battery_soc_after": alloc["battery_soc_after"],
            "current_load": curr_load,
            "estimated_grid_cost": alloc["estimated_grid_cost"],
            "baseline_grid_cost": alloc["baseline_grid_cost"],
            "cost_savings_inr": alloc["cost_savings_inr"],
            "savings_pct_vs_grid": alloc["savings_pct_vs_grid"],
            "grid_dependency_pct": alloc["grid_dependency_pct"],
            "power_balance_verified": alloc["power_balance_verified"],
            "balance_error_kw": alloc["balance_error_kw"],
            "unsafe_action_rejected": alloc["unsafe_action_rejected"],
            "rejection_reason": alloc["rejection_reason"],
            "q_values": q_values,
            "xai": xai,
            "reason": xai["explanation"]
        }

_service_instance: Optional[EnergyRecommenderService] = None

def get_recommender_service() -> EnergyRecommenderService:
    global _service_instance
    if _service_instance is None:
        _service_instance = EnergyRecommenderService()
    return _service_instance

def recommend_energy(state: Union[Dict[str, Any], List[float], np.ndarray]) -> Dict[str, Any]:
    service = get_recommender_service()
    return service.recommend_energy(state)
