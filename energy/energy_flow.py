import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from config.settings import (
    BATTERY_CAPACITY_KWH,
    BATTERY_MIN_SOC,
    BATTERY_MAX_SOC,
    BATTERY_CHARGE_EFFICIENCY,
    BATTERY_DISCHARGE_EFFICIENCY,
    BATTERY_MAX_CHARGE_KW,
    BATTERY_MAX_DISCHARGE_KW,
    DESIRED_BACKUP_HOURS,
    AVERAGE_HOUSEHOLD_LOAD_KW
)
from energy.battery_manager import BatteryManager
from energy.backup_calculator import BackupCalculator
from energy.energy_state import get_energy_state_manager

logger = logging.getLogger("SEMS.EnergyFlow")

class EnergyFlowManager:
    """
    Core Deterministic Energy Flow & Storage Management Layer.
    Strictly follows: SOLAR -> HOUSEHOLD LOAD -> BATTERY -> GRID
    Enforces exact physical energy balance and non-hardcoded 10-hour backup metrics.
    """
    def __init__(
        self,
        capacity_kwh: float = BATTERY_CAPACITY_KWH,
        min_soc: float = BATTERY_MIN_SOC,
        max_soc: float = BATTERY_MAX_SOC,
        desired_backup_hours: float = DESIRED_BACKUP_HOURS,
        avg_load_kw: float = AVERAGE_HOUSEHOLD_LOAD_KW
    ):
        self.capacity_kwh = float(capacity_kwh)
        self.min_soc = float(min_soc)
        self.max_soc = float(max_soc)
        self.battery_manager = BatteryManager(
            capacity_kwh=self.capacity_kwh,
            min_soc=self.min_soc,
            max_soc=self.max_soc
        )
        self.backup_calculator = BackupCalculator(
            capacity_kwh=self.capacity_kwh,
            min_soc=self.min_soc,
            max_soc=self.max_soc,
            default_desired_backup_hours=desired_backup_hours,
            default_avg_load_kw=avg_load_kw
        )
        self.state_manager = get_energy_state_manager()

    def process_realtime_flow(
        self,
        solar_generation_kw: float,
        household_demand_kw: float,
        current_soc: Optional[float] = None,
        dt_hours: float = 0.05,
        grid_available: bool = True,
        tariff_price_inr: float = 4.70,
        user_budget: float = 25.0
    ) -> Dict[str, Any]:
        """
        Executes real-time energy allocation:
        Priority:
          1. Solar -> Household Load
          2. If Solar > Load: Excess Solar -> Battery Charging (up to MAX_SOC & MAX_CHARGE_KW)
             If Battery Full: Remaining Excess -> Grid Export
          3. If Solar < Load: Battery Discharges to supply unmet load (down to MIN_SOC & MAX_DISCHARGE_KW)
             If Battery cannot meet remaining load: Grid supplies deficit
          4. Verifies exact Energy Balance:
             Solar + Battery_Discharge + Grid_Power == Household_Load + Battery_Charge + Grid_Export
        """
        now_utc = datetime.now(timezone.utc)
        solar_kw = max(0.0, float(solar_generation_kw))
        load_kw = max(0.0, float(household_demand_kw))

        # Retrieve current battery state
        persisted_state = self.state_manager.get_state()
        if current_soc is not None:
            soc_start = max(0.0, min(100.0, float(current_soc)))
            energy_start = (soc_start / 100.0) * self.capacity_kwh
        else:
            # Query latest telemetry from configured Battery API (Enode / Sandbox / Demo)
            try:
                from api.battery_api import get_battery_telemetry
                telemetry = get_battery_telemetry()
                if telemetry.get("connected") and telemetry.get("soc_percent") is not None:
                    soc_start = float(telemetry["soc_percent"])
                    if telemetry.get("capacity_kwh"):
                        self.capacity_kwh = float(telemetry["capacity_kwh"])
                        self.battery_manager.capacity_kwh = self.capacity_kwh
                        self.backup_calculator.capacity_kwh = self.capacity_kwh
                    energy_start = (soc_start / 100.0) * self.capacity_kwh
                else:
                    soc_start = float(persisted_state.get("battery_soc", 75.0))
                    energy_start = float(persisted_state.get("battery_energy_kwh", (soc_start / 100.0) * self.capacity_kwh))
            except Exception as e:
                logger.warning(f"Failed to fetch battery telemetry for energy flow: {e}")
                soc_start = float(persisted_state.get("battery_soc", 75.0))
                energy_start = float(persisted_state.get("battery_energy_kwh", (soc_start / 100.0) * self.capacity_kwh))

        battery_charge_kw = 0.0
        battery_discharge_kw = 0.0
        battery_mode = "idle"
        grid_import_kw = 0.0
        grid_export_kw = 0.0
        soc_end = soc_start
        energy_end = energy_start

        if solar_kw >= load_kw:
            # Case 1: Solar is sufficient for Household Load
            excess_solar = solar_kw - load_kw

            if excess_solar > 1e-4:
                # Direct excess solar to charge battery
                charge_power, soc_end, energy_end = self.battery_manager.charge(
                    available_excess_kw=excess_solar,
                    current_energy_kwh=energy_start,
                    dt_hours=dt_hours
                )
                battery_charge_kw = charge_power
                if battery_charge_kw > 0.01:
                    battery_mode = "charging"

                # If solar excess exceeds battery charge acceptance, export rest to grid
                remaining_excess = max(0.0, excess_solar - battery_charge_kw)
                if grid_available:
                    grid_export_kw = round(remaining_excess, 3)
                else:
                    grid_export_kw = 0.0
            else:
                soc_end = soc_start
                energy_end = energy_start

            grid_import_kw = 0.0
            battery_power_display = battery_charge_kw
            if grid_export_kw > 0.05:
                energy_status = "solar_surplus_exporting"
            elif battery_charge_kw > 0.05:
                energy_status = "solar_surplus_charging"
            else:
                energy_status = "solar_self_sufficient"

        else:
            # Case 2: Solar is insufficient for Household Load
            unmet_load = load_kw - solar_kw

            # Battery discharges to cover deficit down to MIN_SOC
            discharge_power, soc_end, energy_end = self.battery_manager.discharge(
                requested_deficit_kw=unmet_load,
                current_energy_kwh=energy_start,
                dt_hours=dt_hours
            )
            battery_discharge_kw = discharge_power
            if battery_discharge_kw > 0.01:
                battery_mode = "discharging"

            # Grid supplies remaining deficit
            remaining_deficit = max(0.0, unmet_load - battery_discharge_kw)
            if grid_available:
                grid_import_kw = round(remaining_deficit, 3)
            else:
                grid_import_kw = 0.0  # Outage: load would shed or under-supply

            grid_export_kw = 0.0
            battery_power_display = battery_discharge_kw

            if grid_import_kw <= 0.01:
                energy_status = "solar_plus_battery"
            elif battery_discharge_kw > 0.01:
                energy_status = "solar_battery_grid"
            else:
                energy_status = "solar_plus_grid"

        # Energy Balance Validation
        # Total generation/import = Solar + Battery_Discharge + Grid_Import
        # Total consumption/export = Household_Load + Battery_Charge + Grid_Export
        total_supply = solar_kw + battery_discharge_kw + grid_import_kw
        total_demand = load_kw + battery_charge_kw + grid_export_kw
        balance_error = abs(total_supply - total_demand)

        # Micro-correction if floating point epsilon occurs
        if 0.0 < balance_error <= 0.01:
            if solar_kw >= load_kw:
                grid_export_kw = max(0.0, round(solar_kw - load_kw - battery_charge_kw, 3))
            else:
                grid_import_kw = max(0.0, round(load_kw - solar_kw - battery_discharge_kw, 3))
            total_supply = solar_kw + battery_discharge_kw + grid_import_kw
            total_demand = load_kw + battery_charge_kw + grid_export_kw
            balance_error = abs(total_supply - total_demand)

        is_balance_valid = balance_error <= 1e-3

        # Backup calculations
        backup_metrics = self.backup_calculator.calculate_backup_metrics(
            current_soc=soc_end,
            current_load_kw=load_kw,
            battery_capacity_kwh=self.capacity_kwh
        )

        # Update persistent energy state
        updated_state = self.state_manager.update_energy_state(
            new_soc=soc_end,
            new_energy_kwh=energy_end,
            battery_power_kw=battery_power_display,
            battery_mode=battery_mode,
            solar_power_kw=solar_kw,
            household_load_kw=load_kw,
            grid_power_kw=grid_import_kw,
            grid_export_kw=grid_export_kw,
            dt_hours=dt_hours,
            tariff_price_inr=tariff_price_inr
        )

        estimated_cost = round(grid_import_kw * dt_hours * tariff_price_inr, 4)
        budget_status = "Within Budget" if estimated_cost <= user_budget else "Budget Exceeded"
        backup_status = "10-Hour Backup Available" if backup_metrics["backup_target_satisfied"] else "10-Hour Backup Not Available"
        
        has_solar = solar_kw > 0.01
        has_battery = battery_discharge_kw > 0.01
        has_grid = grid_import_kw > 0.01
        if has_solar and not has_battery and not has_grid:
            strategy_name = "SOLAR ONLY"
        elif has_solar and has_battery and not has_grid:
            strategy_name = "SOLAR + BATTERY"
        elif has_solar and not has_battery and has_grid:
            strategy_name = "SOLAR + GRID"
        elif not has_solar and has_battery and has_grid:
            strategy_name = "BATTERY + GRID"
        elif has_solar and has_battery and has_grid:
            strategy_name = "SOLAR + BATTERY + GRID"
        elif not has_solar and not has_battery and has_grid:
            strategy_name = "GRID ONLY"
        elif not has_solar and has_battery and not has_grid:
            strategy_name = "BATTERY ONLY"
        else:
            strategy_name = "SOLAR ONLY"

        return {
            "solar_power_kw": round(solar_kw, 3),
            "household_load_kw": round(load_kw, 3),
            "battery_power_kw": round(battery_power_display, 3),
            "battery_mode": battery_mode,
            "battery_soc_before": round(soc_start, 1),
            "battery_soc_after": round(soc_end, 1),
            "battery_soc": round(soc_end, 1),
            "battery_capacity_kwh": self.capacity_kwh,
            "available_battery_energy_kwh": backup_metrics["available_battery_energy_kwh"],
            "grid_power_kw": round(grid_import_kw, 3),
            "grid_export_kw": round(grid_export_kw, 3),
            "estimated_cost": estimated_cost,
            "user_budget": float(user_budget),
            "budget_status": budget_status,
            "estimated_backup_hours": backup_metrics["estimated_backup_hours"],
            "required_backup_hours": int(backup_metrics["required_backup_hours"]),
            "ten_hour_backup_available": backup_metrics.get("ten_hour_backup_available", backup_metrics["backup_target_satisfied"]),
            "backup_status": backup_status,
            "backup_target_satisfied": backup_metrics["backup_target_satisfied"],
            "backup_status_label": backup_metrics["status_label"],
            "energy_strategy": strategy_name,
            "energy_status": energy_status,
            "energy_balance_valid": is_balance_valid,
            "energy_balance_error_kw": round(balance_error, 4),
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

_flow_manager_instance: Optional[EnergyFlowManager] = None

def get_energy_flow_manager() -> EnergyFlowManager:
    global _flow_manager_instance
    if _flow_manager_instance is None:
        _flow_manager_instance = EnergyFlowManager()
    return _flow_manager_instance

def simulate_energy_flow(
    solar_kw: float,
    load_kw: float,
    soc: Optional[float] = None,
    dt_hours: float = 0.05
) -> Dict[str, Any]:
    return get_energy_flow_manager().process_realtime_flow(
        solar_generation_kw=solar_kw,
        household_demand_kw=load_kw,
        current_soc=soc,
        dt_hours=dt_hours
    )
