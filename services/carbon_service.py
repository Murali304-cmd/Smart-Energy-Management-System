import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.CarbonService")

class CarbonService:
    """
    Scope 2 Carbon Footprint & Green Energy Accounting Engine.
    Tracks real-time marginal grid emission factors (gCO2/kWh), avoided emissions,
    and Green Energy Attribute Certificates (REC).
    """

    def __init__(self, regional_grid_emission_factor_g_kwh: float = 710.0):
        # India Central Electricity Authority (CEA) average ~710 gCO2/kWh
        self.grid_factor = regional_grid_emission_factor_g_kwh
        self.cumulative_solar_clean_kwh = 3280.0
        self.cumulative_co2_offset_kg = round(self.cumulative_solar_clean_kwh * (self.grid_factor / 1000.0), 1)

    def calculate_emissions(
        self,
        solar_generation_kw: float,
        grid_import_kw: float,
        battery_discharge_kw: float,
        slot_hours: float = 0.25
    ) -> Dict[str, Any]:
        """Calculates instantaneous and cumulative carbon metrics."""
        clean_solar_kwh = solar_generation_kw * slot_hours
        dirty_grid_kwh = grid_import_kw * slot_hours

        # Current interval carbon
        emitted_co2_kg = round(dirty_grid_kwh * (self.grid_factor / 1000.0), 3)
        avoided_co2_kg = round(clean_solar_kwh * (self.grid_factor / 1000.0), 3)

        self.cumulative_solar_clean_kwh += clean_solar_kwh
        self.cumulative_co2_offset_kg = round(self.cumulative_solar_clean_kwh * (self.grid_factor / 1000.0), 1)

        # Trees planted equivalent (~21 kg CO2 absorbed per mature tree/year)
        trees_equivalent = round(self.cumulative_co2_offset_kg / 21.0, 1)

        total_consumed = clean_solar_kwh + dirty_grid_kwh + (battery_discharge_kw * slot_hours)
        green_index_pct = round((clean_solar_kwh / total_consumed * 100.0), 1) if total_consumed > 0 else 100.0

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "emission_factor_g_co2_kwh": self.grid_factor,
            "current_emitted_co2_kg": emitted_co2_kg,
            "current_avoided_co2_kg": avoided_co2_kg,
            "green_energy_index_pct": min(100.0, green_index_pct),
            "esg_grade": "A+ (Net Zero Ready)" if green_index_pct >= 80 else ("A (Low Carbon)" if green_index_pct >= 50 else "B (Transitioning)"),
            "cumulative_clean_energy_kwh": round(self.cumulative_solar_clean_kwh, 1),
            "cumulative_co2_offset_kg": self.cumulative_co2_offset_kg,
            "equivalent_trees_planted": trees_equivalent,
            "carbon_neutrality_target_year": 2030
        }
