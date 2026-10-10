import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.TariffEngine")

class TariffEngine:
    """
    Advanced Dynamic Multi-Tariff Engine.
    Supports Time-of-Day (ToD), Critical Peak Pricing (CPP), Real-Time Pricing (RTP),
    and Monthly Maximum kVA Demand Charges (TNEB LT/HT Tariff standards).
    """

    def __init__(self, tariff_structure: str = "TNEB_TOD_SLAB"):
        self.tariff_structure = tariff_structure
        self.monthly_peak_kva = 4.2
        self.sanctioned_demand_kva = 5.0
        self.demand_charge_per_kva_inr = 150.0  # ₹150/kVA/month

    def get_current_tariff(self, hour: int, month: int, is_critical_event: bool = False) -> Dict[str, Any]:
        """Calculates effective per-kWh rate and tariff slot details."""
        # 1. Critical Peak Pricing (CPP) Override
        if is_critical_event:
            return {
                "tariff_slot": "CRITICAL_PEAK",
                "rate_per_kwh_inr": 12.50,
                "tier_name": "Critical Peak Pricing (Grid Stress Event)",
                "multiplier": 2.5,
                "is_peak": True,
                "feed_in_tariff_inr": 4.50
            }

        # 2. Time-of-Day (ToD) Slabs (TNEB Standard)
        # Peak: 06:00 - 09:00 and 18:00 - 22:00 (+20% surcharge)
        # Normal: 09:00 - 18:00 (Base rate)
        # Off-Peak: 22:00 - 06:00 (-10% rebate)
        if (6 <= hour <= 9) or (18 <= hour <= 22):
            slot = "PEAK_TOD"
            rate = 6.80
            name = "Evening/Morning Peak ToD (+20% Surcharge)"
            is_peak = True
        elif 22 < hour or hour < 6:
            slot = "OFF_PEAK_NIGHT"
            rate = 3.80
            name = "Night Off-Peak Incentive (-15% Discount)"
            is_peak = False
        else:
            slot = "NORMAL_DAY"
            rate = 4.90
            name = "Standard Daytime Tariff"
            is_peak = False

        return {
            "tariff_structure": self.tariff_structure,
            "tariff_slot": slot,
            "rate_per_kwh_inr": rate,
            "tier_name": name,
            "is_peak": is_peak,
            "feed_in_tariff_inr": 3.50,
            "sanctioned_demand_kva": self.sanctioned_demand_kva,
            "current_month_peak_kva": self.monthly_peak_kva
        }

    def evaluate_demand_penalty(self, active_power_kw: float, power_factor: float = 0.95) -> Dict[str, Any]:
        """Monitors apparent power (kVA) to prevent exceeding sanctioned demand."""
        current_kva = round(float(active_power_kw) / float(power_factor), 2)
        if current_kva > self.monthly_peak_kva:
            self.monthly_peak_kva = float(current_kva)

        exceeded = bool(current_kva > self.sanctioned_demand_kva)
        penalty_inr = 0.0
        if exceeded:
            excess_kva = current_kva - self.sanctioned_demand_kva
            penalty_inr = round(float(excess_kva * self.demand_charge_per_kva_inr * 2.0), 2)

        return {
            "current_apparent_kva": float(current_kva),
            "sanctioned_kva": float(self.sanctioned_demand_kva),
            "monthly_recorded_peak_kva": float(self.monthly_peak_kva),
            "demand_exceeded": bool(exceeded),
            "estimated_penalty_inr": float(penalty_inr),
            "status": "WARNING: DEMAND EXCEEDED" if exceeded else "SAFE"
        }
