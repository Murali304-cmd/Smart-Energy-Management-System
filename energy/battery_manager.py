"""
SEMS Battery Manager Module
Coordinates physical BESS parameters, real API data validation,
SOC bounds, charge/discharge efficiency, power constraints, and dynamic backup estimation.
"""

import logging
from typing import Tuple, Dict, Any, Optional

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
from api.battery_api import get_battery_telemetry, get_battery_provider

logger = logging.getLogger("SEMS.BatteryManager")


class BatteryManager:
    """
    Manages physical BESS behavior, API telemetry validation,
    usable energy calculations, and dynamic backup duration.
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

    def fetch_battery_telemetry(self) -> Dict[str, Any]:
        """Fetches the latest normalized telemetry from the configured Battery API provider."""
        return get_battery_telemetry()

    def validate_soc(self, soc: Any) -> Optional[float]:
        """Validates that SOC is a numerical percentage between 0.0 and 100.0."""
        if soc is None:
            return None
        try:
            val = float(soc)
            if 0.0 <= val <= 100.0:
                return round(val, 2)
            logger.warning(f"Invalid SOC percentage received: {soc}")
            return None
        except (ValueError, TypeError):
            return None

    def validate_capacity(self, capacity_kwh: Any) -> Optional[float]:
        """Validates nominal battery capacity."""
        if capacity_kwh is None:
            return None
        try:
            val = float(capacity_kwh)
            if val > 0.0:
                return round(val, 2)
            return None
        except (ValueError, TypeError):
            return None

    def calculate_available_energy(self, current_soc: float, capacity_kwh: Optional[float] = None) -> float:
        """
        Calculates stored energy (kWh) remaining above the MIN_SOC threshold.
        available_energy = max(0, (SOC - MIN_SOC) / 100 * Capacity)
        """
        cap = capacity_kwh if capacity_kwh is not None else self.capacity_kwh
        usable_soc_pct = max(0.0, current_soc - self.min_soc)
        return round((usable_soc_pct / 100.0) * cap, 3)

    def calculate_usable_energy(self, current_soc: float, capacity_kwh: Optional[float] = None) -> float:
        """
        Calculates deliverable electrical energy (kWh) factoring inverter/discharge efficiency.
        usable_energy = Capacity * usable_SOC_fraction * discharge_efficiency
        """
        avail = self.calculate_available_energy(current_soc, capacity_kwh)
        return round(avail * self.discharge_efficiency, 3)

    def check_min_soc(self, soc: float) -> bool:
        """Returns True if battery SOC is strictly above MIN_SOC threshold."""
        return float(soc) > self.min_soc

    def check_max_soc(self, soc: float) -> bool:
        """Returns True if battery SOC is below MAX_SOC threshold."""
        return float(soc) < self.max_soc

    def check_charge_limit(self, requested_charge_kw: float) -> float:
        """Clamps requested charging power to hardware limits."""
        return max(0.0, min(float(requested_charge_kw), self.max_charge_kw))

    def check_discharge_limit(self, requested_discharge_kw: float) -> float:
        """Clamps requested discharging power to hardware limits."""
        return max(0.0, min(float(requested_discharge_kw), self.max_discharge_kw))

    def check_battery_availability(self) -> Tuple[bool, str]:
        """Checks whether the physical battery is connected and operational."""
        telemetry = self.fetch_battery_telemetry()
        connected = telemetry.get("connected", False)
        mode = telemetry.get("mode", "demo")
        status = telemetry.get("status", "idle")
        if connected and status != "unavailable":
            return True, f"Battery connected ({mode.upper()})"
        return False, telemetry.get("error", "Battery unavailable")

    def calculate_estimated_backup_duration(
        self,
        current_soc: float,
        expected_household_load_kw: float = AVERAGE_HOUSEHOLD_LOAD_KW,
        capacity_kwh: Optional[float] = None
    ) -> float:
        """
        Calculates physical backup hours remaining based on current load and discharge efficiency.
        backup_hours = usable_energy / expected_household_load_kw
        """
        load = max(0.1, float(expected_household_load_kw))
        usable_energy = self.calculate_usable_energy(current_soc, capacity_kwh)
        return round(usable_energy / load, 1)

    def get_available_energy_kwh(self, current_soc: float) -> float:
        """Backward-compatible helper for available energy."""
        return self.calculate_available_energy(current_soc)

    def charge(
        self,
        available_excess_kw: float,
        current_energy_kwh: float,
        dt_hours: float = 0.25
    ) -> Tuple[float, float, float]:
        """
        Charges the battery using excess solar generation.
        Returns:
            (terminal_charging_power_kw, new_soc, new_energy_kwh)
        """
        if available_excess_kw <= 0.0 or dt_hours <= 0.0:
            soc = (current_energy_kwh / self.capacity_kwh) * 100.0
            return 0.0, round(soc, 2), round(current_energy_kwh, 4)

        max_allowed_energy = (self.max_soc / 100.0) * self.capacity_kwh
        energy_headroom = max(0.0, max_allowed_energy - current_energy_kwh)

        if energy_headroom <= 1e-4:
            soc = (current_energy_kwh / self.capacity_kwh) * 100.0
            return 0.0, round(min(self.max_soc, soc), 2), round(min(max_allowed_energy, current_energy_kwh), 4)

        # 1. Terminal power limit
        terminal_power = min(available_excess_kw, self.max_charge_kw)

        # 2. Maximum power battery can accept before hitting MAX_SOC
        max_power_by_headroom = energy_headroom / (dt_hours * self.charge_efficiency)
        actual_charging_power = min(terminal_power, max_power_by_headroom)
        actual_charging_power = max(0.0, actual_charging_power)

        # 3. Energy added into battery cells
        energy_added = actual_charging_power * dt_hours * self.charge_efficiency
        new_energy = min(max_allowed_energy, current_energy_kwh + energy_added)
        new_soc = (new_energy / self.capacity_kwh) * 100.0

        return round(actual_charging_power, 3), round(min(self.max_soc, new_soc), 2), round(new_energy, 4)

    def discharge(
        self,
        requested_deficit_kw: float,
        current_energy_kwh: float,
        dt_hours: float = 0.25
    ) -> Tuple[float, float, float]:
        """
        Discharges the battery to supply unmet household load down to MIN_SOC.
        Returns:
            (terminal_discharging_power_kw, new_soc, new_energy_kwh)
        """
        if requested_deficit_kw <= 0.0 or dt_hours <= 0.0:
            soc = (current_energy_kwh / self.capacity_kwh) * 100.0
            return 0.0, round(soc, 2), round(current_energy_kwh, 4)

        min_allowed_energy = (self.min_soc / 100.0) * self.capacity_kwh
        usable_energy = max(0.0, current_energy_kwh - min_allowed_energy)

        if usable_energy <= 1e-4:
            soc = (current_energy_kwh / self.capacity_kwh) * 100.0
            return 0.0, round(soc, 2), round(current_energy_kwh, 4)

        # Maximum deliverable terminal power based on usable stored energy and efficiency
        max_power_by_energy = (usable_energy * self.discharge_efficiency) / dt_hours
        deliverable_power = min(requested_deficit_kw, min(self.max_discharge_kw, max_power_by_energy))
        deliverable_power = max(0.0, deliverable_power)

        if deliverable_power <= 0.0:
            soc = (current_energy_kwh / self.capacity_kwh) * 100.0
            return 0.0, round(soc, 2), round(current_energy_kwh, 4)

        # Internal chemical energy extracted from cells
        energy_extracted = (deliverable_power * dt_hours) / self.discharge_efficiency
        new_energy = max(min_allowed_energy, current_energy_kwh - energy_extracted)
        new_soc = (new_energy / self.capacity_kwh) * 100.0

        return round(deliverable_power, 3), round(max(self.min_soc, new_soc), 2), round(new_energy, 4)
