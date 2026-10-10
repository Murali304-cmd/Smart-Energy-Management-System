"""
SEMS Deterministic Energy Allocation Layer
Strict physical priority enforcement:
    ☀️ SOLAR -> 🏠 LOAD -> 🔋 BATTERY -> ⚡ GRID
Ensures strict physical BESS bounds, hybrid multi-source dispatch,
and exact physical energy balance validation.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from config.settings import (
    BATTERY_CAPACITY_KWH,
    BATTERY_MIN_SOC,
    BATTERY_MAX_SOC,
    BATTERY_MAX_CHARGE_KW,
    BATTERY_MAX_DISCHARGE_KW,
    BATTERY_CHARGE_EFFICIENCY,
    BATTERY_DISCHARGE_EFFICIENCY
)
from energy.battery_manager import BatteryManager

logger = logging.getLogger("SEMS.EnergyAllocator")

class EnergyAllocationError(ValueError):
    """Raised when physical energy balance or allocation constraints are violated."""
    pass

class EnergyAllocator:
    """
    Deterministic energy allocator for SEMS.
    Implements physical allocation rules across Solar, Load, Battery, and Grid.
    """

    def __init__(
        self,
        capacity_kwh: float = BATTERY_CAPACITY_KWH,
        min_soc: float = BATTERY_MIN_SOC,
        max_soc: float = BATTERY_MAX_SOC,
        max_charge_kw: float = BATTERY_MAX_CHARGE_KW,
        max_discharge_kw: float = BATTERY_MAX_DISCHARGE_KW,
        charge_efficiency: float = BATTERY_CHARGE_EFFICIENCY,
        discharge_efficiency: float = BATTERY_DISCHARGE_EFFICIENCY
    ):
        self.capacity_kwh = float(capacity_kwh)
        self.min_soc = float(min_soc)
        self.max_soc = float(max_soc)
        self.max_charge_kw = float(max_charge_kw)
        self.max_discharge_kw = float(max_discharge_kw)
        self.charge_efficiency = float(charge_efficiency)
        self.discharge_efficiency = float(discharge_efficiency)
        self.battery_manager = BatteryManager(
            capacity_kwh=self.capacity_kwh,
            min_soc=self.min_soc,
            max_soc=self.max_soc,
            max_charge_kw=self.max_charge_kw,
            max_discharge_kw=self.max_discharge_kw,
            charge_efficiency=self.charge_efficiency,
            discharge_efficiency=self.discharge_efficiency
        )

    def allocate(
        self,
        solar_generation_kw: float,
        household_demand_kw: float,
        battery_soc: float,
        dt_hours: float = 0.25,
        grid_available: bool = True
    ) -> Dict[str, Any]:
        """
        Allocates power following the strict hierarchy:
            ☀️ SOLAR -> 🏠 LOAD -> 🔋 BATTERY -> ⚡ GRID

        Returns detailed power allocation and updated battery state.
        Raises EnergyAllocationError if energy balance validation fails.
        """
        solar_kw = max(0.0, float(solar_generation_kw))
        demand_kw = max(0.0, float(household_demand_kw))
        soc_before = max(0.0, min(100.0, float(battery_soc)))
        dt = max(1e-4, float(dt_hours))

        # Battery initial chemical energy (kWh)
        energy_start = (soc_before / 100.0) * self.capacity_kwh

        # Initialize allocation quantities
        solar_to_load = 0.0
        excess_solar = 0.0
        battery_charge_kw = 0.0
        battery_discharge_kw = 0.0
        grid_power_kw = 0.0
        grid_export_kw = 0.0
        soc_after = soc_before
        energy_after = energy_start
        battery_mode = "idle"

        # -----------------------------------------------------------------
        # STEP 1: SOLAR DISPATCH (Priority 1)
        # Solar must always be used first for the household load.
        # -----------------------------------------------------------------
        if solar_kw >= demand_kw:
            # Solar covers the entire household load
            solar_to_load = demand_kw
            excess_solar = solar_kw - demand_kw

            # -----------------------------------------------------------------
            # STEP 2: SOLAR SURPLUS -> BATTERY CHARGING (Priority 2)
            # -----------------------------------------------------------------
            if excess_solar > 1e-4:
                charge_power, soc_after, energy_after = self.battery_manager.charge(
                    available_excess_kw=excess_solar,
                    current_energy_kwh=energy_start,
                    dt_hours=dt
                )
                battery_charge_kw = charge_power
                if battery_charge_kw > 0.01:
                    battery_mode = "charging"

                # If battery is full or max charge rate reached: Remaining excess solar -> Grid Export
                remaining_excess = max(0.0, excess_solar - battery_charge_kw)
                if grid_available:
                    grid_export_kw = round(remaining_excess, 3)
                else:
                    grid_export_kw = 0.0

            grid_power_kw = 0.0
            battery_power_display = battery_charge_kw

        else:
            # Solar is insufficient for the household load
            solar_to_load = solar_kw
            unmet_demand = demand_kw - solar_to_load

            # -----------------------------------------------------------------
            # STEP 3: SOLAR DEFICIT -> BATTERY DISCHARGE (Priority 3)
            # Never discharge battery below MIN_SOC.
            # -----------------------------------------------------------------
            discharge_power, soc_after, energy_after = self.battery_manager.discharge(
                requested_deficit_kw=unmet_demand,
                current_energy_kwh=energy_start,
                dt_hours=dt
            )
            battery_discharge_kw = discharge_power
            if battery_discharge_kw > 0.01:
                battery_mode = "discharging"

            # -----------------------------------------------------------------
            # STEP 4: GRID BACKUP (Priority 4)
            # Grid should only be used when Solar + Battery < Household Demand.
            # Formula: grid_power = max(0, household_demand - solar_power - battery_power)
            # -----------------------------------------------------------------
            remaining_deficit = max(0.0, unmet_demand - battery_discharge_kw)
            if grid_available:
                grid_power_kw = round(remaining_deficit, 3)
            else:
                grid_power_kw = 0.0

            grid_export_kw = 0.0
            battery_power_display = battery_discharge_kw

        # -----------------------------------------------------------------
        # STEP 5: HYBRID STRATEGY CLASSIFICATION
        # Supports: Solar only, Solar + Battery, Solar + Grid, Battery + Grid,
        #           Solar + Battery + Grid, Grid only, Battery only
        # -----------------------------------------------------------------
        strategy = self._determine_strategy(
            solar_to_load=solar_to_load,
            battery_discharge_kw=battery_discharge_kw,
            grid_power_kw=grid_power_kw
        )

        # -----------------------------------------------------------------
        # STEP 6: ENERGY BALANCE VALIDATION
        # Formula:
        # Solar Power + Battery Discharge + Grid Power
        #   == Household Load + Battery Charging + Grid Export
        # -----------------------------------------------------------------
        total_supply = solar_kw + battery_discharge_kw + grid_power_kw
        total_demand = demand_kw + battery_charge_kw + grid_export_kw
        balance_error = abs(total_supply - total_demand)

        # Micro-correction for 64-bit floating point epsilon (< 0.005 kW)
        if 0.0 < balance_error <= 0.005:
            if solar_kw >= demand_kw:
                grid_export_kw = max(0.0, round(solar_kw - demand_kw - battery_charge_kw, 3))
            else:
                grid_power_kw = max(0.0, round(demand_kw - solar_to_load - battery_discharge_kw, 3))
            total_supply = solar_kw + battery_discharge_kw + grid_power_kw
            total_demand = demand_kw + battery_charge_kw + grid_export_kw
            balance_error = abs(total_supply - total_demand)

        is_balance_valid = balance_error <= 1e-3

        if not is_balance_valid:
            err_msg = (
                f"Energy balance violation detected: Supply ({total_supply:.4f} kW) != "
                f"Demand/Storage ({total_demand:.4f} kW) with error {balance_error:.4f} kW."
            )
            logger.error(err_msg)
            raise EnergyAllocationError(err_msg)

        available_battery_energy_kwh = self.battery_manager.get_available_energy_kwh(soc_after)

        return {
            "solar_power_kw": round(solar_kw, 3),
            "solar_to_load_kw": round(solar_to_load, 3),
            "household_load_kw": round(demand_kw, 3),
            "battery_power_kw": round(battery_power_display, 3),
            "battery_charge_kw": round(battery_charge_kw, 3),
            "battery_discharge_kw": round(battery_discharge_kw, 3),
            "battery_mode": battery_mode,
            "battery_soc_before": round(soc_before, 2),
            "battery_soc_after": round(soc_after, 2),
            "battery_energy_kwh": round(energy_after, 4),
            "available_battery_energy_kwh": available_battery_energy_kwh,
            "grid_power_kw": round(grid_power_kw, 3),
            "grid_export_kw": round(grid_export_kw, 3),
            "energy_strategy": strategy,
            "energy_balance_valid": True,
            "energy_balance_error_kw": round(balance_error, 5)
        }

    @staticmethod
    def _determine_strategy(
        solar_to_load: float,
        battery_discharge_kw: float,
        grid_power_kw: float
    ) -> str:
        """Determines the operational hybrid strategy label."""
        has_solar = solar_to_load > 0.01
        has_battery = battery_discharge_kw > 0.01
        has_grid = grid_power_kw > 0.01

        if has_solar and not has_battery and not has_grid:
            return "SOLAR ONLY"
        elif has_solar and has_battery and not has_grid:
            return "SOLAR + BATTERY"
        elif has_solar and not has_battery and has_grid:
            return "SOLAR + GRID"
        elif not has_solar and has_battery and has_grid:
            return "BATTERY + GRID"
        elif has_solar and has_battery and has_grid:
            return "SOLAR + BATTERY + GRID"
        elif not has_solar and not has_battery and has_grid:
            return "GRID ONLY"
        elif not has_solar and has_battery and not has_grid:
            return "BATTERY ONLY"
        else:
            return "SOLAR ONLY"
