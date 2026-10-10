"""
SEMS Dynamic Backup Calculator Module
Computes authentic, non-hardcoded battery backup duration based on:
    usable_energy_kwh = battery_capacity_kwh * usable_SOC_fraction * battery_efficiency
    backup_hours = usable_energy_kwh / expected_household_load_kw
Never guarantees 10 hours if not physically available.
"""

import logging
from typing import Dict, Any, Optional

from config.settings import (
    BATTERY_CAPACITY_KWH,
    BATTERY_MIN_SOC,
    BATTERY_MAX_SOC,
    BATTERY_DISCHARGE_EFFICIENCY,
    DESIRED_BACKUP_HOURS,
    AVERAGE_HOUSEHOLD_LOAD_KW
)

logger = logging.getLogger("SEMS.BackupCalculator")


class BackupCalculator:
    """
    Calculates dynamic battery backup duration and capacity requirements.
    Never hardcodes 10 hours; computes actual physical duration based on
    load, available energy, SOC bounds, and discharge efficiency.
    """
    def __init__(
        self,
        capacity_kwh: float = BATTERY_CAPACITY_KWH,
        min_soc: float = BATTERY_MIN_SOC,
        max_soc: float = BATTERY_MAX_SOC,
        discharge_efficiency: float = BATTERY_DISCHARGE_EFFICIENCY,
        default_desired_backup_hours: float = DESIRED_BACKUP_HOURS,
        default_avg_load_kw: float = AVERAGE_HOUSEHOLD_LOAD_KW
    ):
        self.capacity_kwh = float(capacity_kwh)
        self.min_soc = float(min_soc)
        self.max_soc = float(max_soc)
        self.discharge_efficiency = float(discharge_efficiency)
        self.desired_backup_hours = float(default_desired_backup_hours)
        self.avg_load_kw = float(default_avg_load_kw)

    def calculate_required_capacity(
        self,
        desired_hours: Optional[float] = None,
        avg_load_kw: Optional[float] = None
    ) -> float:
        """
        Calculates the required nominal battery capacity (kWh) to sustain
        average load for the desired backup hours, factoring in MIN_SOC, MAX_SOC,
        and discharge efficiency.
        """
        hours = float(desired_hours if desired_hours is not None else self.desired_backup_hours)
        load = float(avg_load_kw if avg_load_kw is not None else self.avg_load_kw)

        # Usable energy required at household terminals
        required_usable_energy = load * hours

        # Nominal capacity required to provide this usable energy
        usable_fraction = max(0.1, (self.max_soc - self.min_soc) / 100.0)
        required_nominal_capacity = required_usable_energy / (usable_fraction * self.discharge_efficiency)
        return round(required_nominal_capacity, 1)

    def calculate_backup_metrics(
        self,
        current_soc: float,
        current_load_kw: float,
        desired_hours: Optional[float] = None,
        avg_load_kw: Optional[float] = None,
        battery_capacity_kwh: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Computes comprehensive backup statistics:
        - usable_energy_kwh = battery_capacity_kwh * usable_SOC_fraction * battery_efficiency
        - backup_hours = usable_energy_kwh / expected_household_load_kw
        - ten_hour_backup_available: boolean (backup_hours >= 10.0)
        """
        target_hours = float(desired_hours if desired_hours is not None else self.desired_backup_hours)
        avg_load = float(avg_load_kw if avg_load_kw is not None else self.avg_load_kw)
        cap = float(battery_capacity_kwh if battery_capacity_kwh is not None else self.capacity_kwh)

        # Usable SOC fraction above MIN_SOC
        usable_soc_fraction = max(0.0, (current_soc - self.min_soc) / 100.0)

        # Available Stored Energy (kWh) in battery cells
        available_energy_kwh = round(cap * usable_soc_fraction, 3)

        # Deliverable electrical energy factoring discharge efficiency
        usable_energy_kwh = round(cap * usable_soc_fraction * self.discharge_efficiency, 3)

        # Effective expected load for estimation
        effective_load = current_load_kw if current_load_kw > 0.05 else avg_load
        effective_load = max(0.1, effective_load)

        # Estimated backup hours at current load
        estimated_hours = round(usable_energy_kwh / effective_load, 1)

        # Backup hours at baseline average load
        estimated_hours_at_avg = round(usable_energy_kwh / max(0.1, avg_load), 1)

        # Required nominal capacity for 10-hour backup target
        required_cap = self.calculate_required_capacity(target_hours, avg_load)

        # 10-Hour backup compliance
        ten_hour_available = estimated_hours >= target_hours
        backup_status = "10-hour backup available" if ten_hour_available else "10-hour backup not available"

        shortfall_hours = round(max(0.0, target_hours - estimated_hours), 1)
        adequacy_pct = min(100.0, round((estimated_hours / max(0.1, target_hours)) * 100.0, 1))

        if ten_hour_available:
            status_label = f"10-Hour Backup Available ({estimated_hours}h at {effective_load:.2f} kW load)"
            status_level = "optimal"
        elif estimated_hours >= (target_hours * 0.5):
            status_label = f"10-Hour Backup Not Available ({estimated_hours}h estimated vs {target_hours}h target)"
            status_level = "moderate"
        else:
            status_label = f"10-Hour Backup Not Available ({estimated_hours}h estimated, {shortfall_hours}h shortfall)"
            status_level = "low"

        return {
            "capacity_kwh": cap,
            "current_battery_capacity_kwh": cap,
            "usable_energy_kwh": usable_energy_kwh,
            "available_battery_energy_kwh": round(available_energy_kwh, 2),
            "deliverable_energy_kwh": round(usable_energy_kwh, 2),
            "expected_load_kw": round(effective_load, 2),
            "estimated_backup_hours": estimated_hours,
            "estimated_backup_hours_avg_load": estimated_hours_at_avg,
            "required_backup_hours": target_hours,
            "ten_hour_backup_available": ten_hour_available,
            "backup_target_satisfied": ten_hour_available,
            "backup_status": backup_status,
            "backup_shortfall_hours": shortfall_hours,
            "backup_adequacy_pct": adequacy_pct,
            "status_label": status_label,
            "status_level": status_level,
            "min_soc": self.min_soc,
            "current_soc": round(current_soc, 1),
            "required_battery_capacity_kwh": required_cap
        }
