"""
SEMS Central Energy Management Module
Coordinates:
    ML Predictions -> DQN Decision -> ENERGY MANAGEMENT
        ├── Cost Optimization
        ├── Energy Allocation
        ├── Battery Management
        └── Grid Management
    -> Solar -> Battery -> Grid -> XAI -> Dashboard -> Notifications
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union, List

from config.settings import (
    BATTERY_CAPACITY_KWH,
    BATTERY_MIN_SOC,
    BATTERY_MAX_SOC,
    BATTERY_MAX_CHARGE_KW,
    BATTERY_MAX_DISCHARGE_KW,
    BATTERY_CHARGE_EFFICIENCY,
    BATTERY_DISCHARGE_EFFICIENCY,
    DESIRED_BACKUP_HOURS,
    AVERAGE_HOUSEHOLD_LOAD_KW
)
from energy.battery_manager import BatteryManager
from energy.backup_calculator import BackupCalculator
from energy.cost_optimizer import CostOptimizer
from energy.energy_allocator import EnergyAllocator, EnergyAllocationError
from energy.energy_state import get_energy_state_manager

logger = logging.getLogger("SEMS.EnergyManager")

class EnergyManager:
    """
    Central Energy Management System (SEMS) Controller.
    Integrates ML predictions, DQN policy, deterministic allocation,
    BESS physical bounds, cost optimization, and dynamic 10-hour backup calculations.
    """

    def __init__(
        self,
        capacity_kwh: float = BATTERY_CAPACITY_KWH,
        min_soc: float = BATTERY_MIN_SOC,
        max_soc: float = BATTERY_MAX_SOC,
        max_charge_kw: float = BATTERY_MAX_CHARGE_KW,
        max_discharge_kw: float = BATTERY_MAX_DISCHARGE_KW,
        charge_efficiency: float = BATTERY_CHARGE_EFFICIENCY,
        discharge_efficiency: float = BATTERY_DISCHARGE_EFFICIENCY,
        required_backup_hours: float = 10.0,
        default_budget: float = 25.0
    ):
        self.capacity_kwh = float(capacity_kwh)
        self.min_soc = float(min_soc)
        self.max_soc = float(max_soc)
        self.max_charge_kw = float(max_charge_kw)
        self.max_discharge_kw = float(max_discharge_kw)
        self.charge_efficiency = float(charge_efficiency)
        self.discharge_efficiency = float(discharge_efficiency)
        self.required_backup_hours = float(required_backup_hours)
        self.default_budget = float(default_budget)

        # Child Services
        self.battery_manager = BatteryManager(
            capacity_kwh=self.capacity_kwh,
            min_soc=self.min_soc,
            max_soc=self.max_soc,
            max_charge_kw=self.max_charge_kw,
            max_discharge_kw=self.max_discharge_kw,
            charge_efficiency=self.charge_efficiency,
            discharge_efficiency=self.discharge_efficiency
        )
        self.backup_calculator = BackupCalculator(
            capacity_kwh=self.capacity_kwh,
            min_soc=self.min_soc,
            max_soc=self.max_soc,
            discharge_efficiency=self.discharge_efficiency,
            default_desired_backup_hours=self.required_backup_hours,
            default_avg_load_kw=AVERAGE_HOUSEHOLD_LOAD_KW
        )
        self.cost_optimizer = CostOptimizer(default_budget=self.default_budget)
        self.allocator = EnergyAllocator(
            capacity_kwh=self.capacity_kwh,
            min_soc=self.min_soc,
            max_soc=self.max_soc,
            max_charge_kw=self.max_charge_kw,
            max_discharge_kw=self.max_discharge_kw,
            charge_efficiency=self.charge_efficiency,
            discharge_efficiency=self.discharge_efficiency
        )
        self.state_manager = get_energy_state_manager()

    def process_energy_decision(
        self,
        predicted_solar: float,
        household_demand: float,
        predicted_price: float,
        battery_soc: Optional[float] = None,
        user_budget: Optional[float] = None,
        dt_hours: float = 0.25,
        grid_available: bool = True,
        dqn_agent: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Executes complete Energy Management workflow:
        1. Reads or overrides battery SOC
        2. Evaluates DQN intelligent policy recommendation
        3. Enforces deterministic allocation hierarchy (Solar -> Load -> Battery -> Grid)
        4. Validates exact energy balance
        5. Computes electricity cost & budget compliance
        6. Calculates physical 10-hour backup duration
        7. Persists real-time energy state and accumulators
        """
        now_utc = datetime.now(timezone.utc)
        solar_val = max(0.0, float(predicted_solar))
        load_val = max(0.1, float(household_demand))
        price_val = max(0.0, float(predicted_price))
        budget_val = float(user_budget if user_budget is not None else self.default_budget)

        # 1. Resolve current battery SOC
        persisted_state = self.state_manager.get_state()
        if battery_soc is not None:
            current_soc = max(0.0, min(100.0, float(battery_soc)))
        else:
            try:
                from api.battery_api import get_battery_telemetry
                telemetry = get_battery_telemetry()
                if telemetry.get("connected") and telemetry.get("soc_percent") is not None:
                    current_soc = float(telemetry["soc_percent"])
                    if telemetry.get("capacity_kwh"):
                        self.capacity_kwh = float(telemetry["capacity_kwh"])
                        self.allocator.capacity_kwh = self.capacity_kwh
                        self.allocator.battery_manager.capacity_kwh = self.capacity_kwh
                        self.backup_calculator.capacity_kwh = self.capacity_kwh
                else:
                    current_soc = float(persisted_state.get("battery_soc", 75.0))
            except Exception as e:
                logger.warning(f"Failed to fetch battery telemetry for EnergyManager: {e}")
                current_soc = float(persisted_state.get("battery_soc", 75.0))

        # 2. DQN State Vector: [predicted_solar, predicted_load, predicted_price, battery_soc, user_demand, user_budget]
        state_vector = [solar_val, load_val, price_val, current_soc, load_val, budget_val]
        dqn_action_id = 0
        q_values = [10.0, 5.0, 2.0, 8.0]

        if dqn_agent is not None:
            try:
                dqn_action_id, q_values = dqn_agent.select_action(state_vector, eval_mode=True)
            except Exception as e:
                logger.warning(f"DQN agent selection failed, using priority hybrid default: {e}")
                dqn_action_id = 0

        # 3. Deterministic Allocation Layer (Solar -> Load -> Battery -> Grid)
        alloc_res = self.allocator.allocate(
            solar_generation_kw=solar_val,
            household_demand_kw=load_val,
            battery_soc=current_soc,
            dt_hours=dt_hours,
            grid_available=grid_available
        )

        solar_kw = alloc_res["solar_power_kw"]
        battery_power_kw = alloc_res["battery_power_kw"]
        battery_mode = alloc_res["battery_mode"]
        soc_before = alloc_res["battery_soc_before"]
        soc_after = alloc_res["battery_soc_after"]
        grid_power_kw = alloc_res["grid_power_kw"]
        grid_export_kw = alloc_res["grid_export_kw"]
        strategy = alloc_res["energy_strategy"]
        energy_balance_valid = alloc_res["energy_balance_valid"]

        # 4. Cost Optimization & Budget Evaluation
        cost_res = self.cost_optimizer.optimize_dispatch_economics(
            household_demand_kw=load_val,
            solar_power_kw=solar_kw,
            battery_power_kw=battery_power_kw,
            grid_power_kw=grid_power_kw,
            dt_hours=dt_hours,
            electricity_price=price_val,
            user_budget=budget_val
        )
        estimated_cost = cost_res["estimated_cost"]
        budget_status = cost_res["budget_status"]
        budget_message = cost_res["budget_message"]

        # 5. 10-Hour Battery Backup Calculation
        backup_metrics = self.backup_calculator.calculate_backup_metrics(
            current_soc=soc_after,
            current_load_kw=load_val,
            desired_hours=self.required_backup_hours,
            battery_capacity_kwh=self.capacity_kwh
        )
        available_energy_kwh = backup_metrics["available_battery_energy_kwh"]
        estimated_backup_hours = backup_metrics["estimated_backup_hours"]
        backup_status = backup_metrics["backup_status"]
        backup_target_satisfied = backup_metrics["backup_target_satisfied"]

        # 6. State Persistence
        updated_state = self.state_manager.update_energy_state(
            new_soc=soc_after,
            new_energy_kwh=alloc_res["battery_energy_kwh"],
            battery_power_kw=battery_power_kw,
            battery_mode=battery_mode,
            solar_power_kw=solar_kw,
            household_load_kw=load_val,
            grid_power_kw=grid_power_kw,
            grid_export_kw=grid_export_kw,
            dt_hours=dt_hours,
            tariff_price_inr=price_val
        )

        # 7. Complete Standard Output Structure
        return {
            "solar_power_kw": solar_kw,
            "household_load_kw": load_val,
            "battery_power_kw": battery_power_kw,
            "battery_mode": battery_mode,
            "battery_soc_before": soc_before,
            "battery_soc_after": soc_after,
            "battery_soc": soc_after,
            "grid_power_kw": grid_power_kw,
            "grid_export_kw": grid_export_kw,
            "estimated_cost": estimated_cost,
            "user_budget": budget_val,
            "budget_status": budget_status,
            "budget_message": budget_message,
            "available_battery_energy_kwh": available_energy_kwh,
            "estimated_backup_hours": estimated_backup_hours,
            "required_backup_hours": int(self.required_backup_hours),
            "ten_hour_backup_available": backup_metrics.get("ten_hour_backup_available", backup_target_satisfied),
            "backup_status": backup_status,
            "backup_target_satisfied": backup_target_satisfied,
            "energy_strategy": strategy,
            "energy_balance_valid": energy_balance_valid,
            "dqn_action_id": dqn_action_id,
            "q_values": q_values,
            "battery_capacity_kwh": self.capacity_kwh,
            "battery_min_soc": self.min_soc,
            "battery_max_soc": self.max_soc,
            "battery_charging_limit_kw": self.max_charge_kw,
            "battery_discharging_limit_kw": self.max_discharge_kw,
            "predicted_price_inr": price_val,
            "cost_savings_inr": cost_res["savings_inr"],
            "timestamp": now_utc.isoformat(),
            "daily_accumulators": {
                "today_solar_kwh": updated_state.get("today_solar_kwh", 0.0),
                "today_load_kwh": updated_state.get("today_load_kwh", 0.0),
                "today_battery_discharge_kwh": updated_state.get("today_battery_discharge_kwh", 0.0),
                "today_grid_import_kwh": updated_state.get("today_grid_import_kwh", 0.0),
                "today_grid_export_kwh": updated_state.get("today_grid_export_kwh", 0.0),
                "today_cost_inr": updated_state.get("today_cost_inr", 0.0)
            }
        }

_energy_manager_instance: Optional[EnergyManager] = None

def get_energy_manager() -> EnergyManager:
    """Returns singleton EnergyManager instance."""
    global _energy_manager_instance
    if _energy_manager_instance is None:
        _energy_manager_instance = EnergyManager()
    return _energy_manager_instance
