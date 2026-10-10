import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.EVOptimizer")

class EVOptimizer:
    """
    Vehicle-to-Grid (V2G) & Vehicle-to-Home (V2H) Bidirectional EV Battery Dispatcher.
    Controls ISO 15118 smart charging/discharging based on solar surplus and grid tariffs.
    """

    def __init__(
        self,
        battery_capacity_kwh: float = 60.0,
        max_charge_kw: float = 7.4,
        max_discharge_kw: float = 5.0,
        min_reserve_soc: float = 40.0
    ):
        self.battery_capacity_kwh = battery_capacity_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw
        self.min_reserve_soc = min_reserve_soc
        self.current_soc = 68.0
        self.connection_status = "CONNECTED"
        self.target_departure_time = "08:00 AM"
        self.target_departure_soc = 85.0
        self.v2h_enabled = True

    def optimize_dispatch(
        self,
        solar_surplus_kw: float,
        grid_price_inr: float,
        is_grid_outage: bool,
        home_load_kw: float
    ) -> Dict[str, Any]:
        """Calculates optimal EV bidirectional power flow setpoint."""
        action = "IDLE"
        power_kw = 0.0
        reason = "Maintaining standby state"

        # 1. Emergency V2H Power Supply during Blackout
        if is_grid_outage:
            if self.current_soc > self.min_reserve_soc:
                action = "V2H_DISCHARGING"
                power_kw = -min(self.max_discharge_kw, home_load_kw)
                reason = f"Supplying {abs(power_kw):.2f} kW to home critical circuits during grid blackout."
            else:
                action = "IDLE"
                reason = f"EV reached minimum safe reserve limit ({self.min_reserve_soc}%)."

        # 2. Solar Surplus Smart Charging
        elif solar_surplus_kw > 1.5 and self.current_soc < self.target_departure_soc:
            action = "SOLAR_SMART_CHARGING"
            power_kw = min(self.max_charge_kw, solar_surplus_kw)
            reason = f"Absorbing {power_kw:.2f} kW clean rooftop solar surplus into EV battery."

        # 3. Peak Tariff V2G / V2H Arbitrage
        elif grid_price_inr >= 6.5 and self.current_soc > (self.min_reserve_soc + 15.0) and self.v2h_enabled:
            action = "V2H_ARBITRAGE"
            power_kw = -min(self.max_discharge_kw, home_load_kw)
            reason = f"Discharging EV battery at high peak tariff (₹{grid_price_inr:.2f}/kWh) to avoid expensive grid purchase."

        # 4. Off-Peak Grid Fast Charge
        elif grid_price_inr <= 3.5 and self.current_soc < self.target_departure_soc:
            action = "OFF_PEAK_CHARGING"
            power_kw = self.max_charge_kw
            reason = f"Charging at lowest off-peak grid rate (₹{grid_price_inr:.2f}/kWh) before morning commute."

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "connection_status": self.connection_status,
            "ev_battery_soc": self.current_soc,
            "target_departure_soc": self.target_departure_soc,
            "target_departure_time": self.target_departure_time,
            "v2h_enabled": self.v2h_enabled,
            "dispatch_action": action,
            "dispatch_power_kw": power_kw,
            "reason": reason,
            "estimated_cost_impact_inr": round(abs(power_kw) * grid_price_inr * 0.25, 2)  # 15min slot
        }

    def set_ev_settings(self, v2h_enabled: bool, min_reserve_soc: float, target_soc: float) -> Dict[str, Any]:
        self.v2h_enabled = v2h_enabled
        self.min_reserve_soc = min_reserve_soc
        self.target_departure_soc = target_soc
        return {
            "status": "success",
            "v2h_enabled": self.v2h_enabled,
            "min_reserve_soc": self.min_reserve_soc,
            "target_departure_soc": self.target_departure_soc
        }
