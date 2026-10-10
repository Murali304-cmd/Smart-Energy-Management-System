import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import (
    BATTERY_CAPACITY_KWH,
    BATTERY_MIN_SOC,
    BATTERY_MAX_SOC,
    BATTERY_STATE_FILE
)

logger = logging.getLogger("SEMS.EnergyState")

class EnergyStateManager:
    """
    Maintains persistent energy state and battery storage across dashboard refreshes,
    API requests, and server restarts.
    """
    _instance: Optional["EnergyStateManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EnergyStateManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, state_file: Optional[Path] = None, capacity_kwh: float = BATTERY_CAPACITY_KWH):
        if getattr(self, "_initialized", False):
            return
        self.state_file = Path(state_file or BATTERY_STATE_FILE)
        self.capacity_kwh = float(capacity_kwh)
        self._op_lock = threading.Lock()
        self._state: Dict[str, Any] = {}
        self._load_or_initialize()
        self._initialized = True

    def _load_or_initialize(self):
        """Loads existing state from json file, or creates realistic initial state."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        default_soc = 75.0
        default_energy = (default_soc / 100.0) * self.capacity_kwh

        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and "battery_soc" in loaded:
                    self._state = loaded
                    if self._state.get("battery_capacity_kwh") != self.capacity_kwh:
                        self._state["battery_capacity_kwh"] = self.capacity_kwh
                        self._state["battery_energy_kwh"] = round((float(self._state.get("battery_soc", 75.0)) / 100.0) * self.capacity_kwh, 4)
                    # Reset daily accumulators if day changed
                    if self._state.get("current_date") != today_str:
                        self._reset_daily_accumulators(today_str)
                    logger.info(f"Loaded persistent battery state: SOC={self._state.get('battery_soc')}%, Energy={self._state.get('battery_energy_kwh')} kWh, Capacity={self.capacity_kwh} kWh")
                    return
            except Exception as e:
                logger.error(f"Failed to read {self.state_file}: {e}, initializing clean state.")

        # Default state
        self._state = {
            "current_date": today_str,
            "battery_soc": default_soc,
            "battery_energy_kwh": round(default_energy, 4),
            "battery_capacity_kwh": self.capacity_kwh,
            "battery_power_kw": 0.0,
            "battery_mode": "idle",
            "solar_power_kw": 0.0,
            "household_load_kw": 1.8,
            "grid_power_kw": 0.0,
            "grid_export_kw": 0.0,
            "today_solar_kwh": 6.8,
            "today_load_kwh": 9.4,
            "today_battery_discharge_kwh": 3.2,
            "today_battery_charge_kwh": 3.5,
            "today_grid_import_kwh": 2.6,
            "today_grid_export_kwh": 0.9,
            "today_cost_inr": 15.60,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        self._save()

    def _reset_daily_accumulators(self, today_str: str):
        self._state["current_date"] = today_str
        self._state["today_solar_kwh"] = 0.0
        self._state["today_load_kwh"] = 0.0
        self._state["today_battery_discharge_kwh"] = 0.0
        self._state["today_battery_charge_kwh"] = 0.0
        self._state["today_grid_import_kwh"] = 0.0
        self._state["today_grid_export_kwh"] = 0.0
        self._state["today_cost_inr"] = 0.0

    def _save(self):
        """Atomically saves the state to disk with Windows fallback."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.state_file.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            try:
                os.replace(tmp_path, self.state_file)
            except Exception:
                with open(self.state_file, "w", encoding="utf-8") as f:
                    json.dump(self._state, f, indent=2)
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Failed to persist state to {self.state_file}: {e}")

    def get_state(self) -> Dict[str, Any]:
        with self._op_lock:
            return dict(self._state)

    def update_energy_state(
        self,
        new_soc: float,
        new_energy_kwh: float,
        battery_power_kw: float,
        battery_mode: str,
        solar_power_kw: float,
        household_load_kw: float,
        grid_power_kw: float,
        grid_export_kw: float,
        dt_hours: float = 0.05,
        tariff_price_inr: float = 4.70
    ) -> Dict[str, Any]:
        """
        Updates state in-memory and on-disk after an energy flow iteration.
        """
        with self._op_lock:
            today_str = datetime.now().strftime("%Y-%m-%d")
            if self._state.get("current_date") != today_str:
                self._reset_daily_accumulators(today_str)

            self._state["battery_soc"] = round(float(new_soc), 2)
            self._state["battery_energy_kwh"] = round(float(new_energy_kwh), 4)
            self._state["battery_power_kw"] = round(float(battery_power_kw), 3)
            self._state["battery_mode"] = battery_mode
            self._state["solar_power_kw"] = round(float(solar_power_kw), 3)
            self._state["household_load_kw"] = round(float(household_load_kw), 3)
            self._state["grid_power_kw"] = round(float(grid_power_kw), 3)
            self._state["grid_export_kw"] = round(float(grid_export_kw), 3)
            self._state["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Increment accumulators
            self._state["today_solar_kwh"] = round(self._state.get("today_solar_kwh", 0.0) + solar_power_kw * dt_hours, 3)
            self._state["today_load_kwh"] = round(self._state.get("today_load_kwh", 0.0) + household_load_kw * dt_hours, 3)
            
            if battery_mode == "charging":
                self._state["today_battery_charge_kwh"] = round(self._state.get("today_battery_charge_kwh", 0.0) + battery_power_kw * dt_hours, 3)
            elif battery_mode == "discharging":
                self._state["today_battery_discharge_kwh"] = round(self._state.get("today_battery_discharge_kwh", 0.0) + battery_power_kw * dt_hours, 3)

            self._state["today_grid_import_kwh"] = round(self._state.get("today_grid_import_kwh", 0.0) + grid_power_kw * dt_hours, 3)
            self._state["today_grid_export_kwh"] = round(self._state.get("today_grid_export_kwh", 0.0) + grid_export_kw * dt_hours, 3)
            cost_increment = (grid_power_kw * dt_hours) * tariff_price_inr
            self._state["today_cost_inr"] = round(self._state.get("today_cost_inr", 0.0) + cost_increment, 2)

            self._save()
            return dict(self._state)

    def set_soc_override(self, target_soc: float):
        """Allows testing or user override if explicitly desired."""
        with self._op_lock:
            soc = max(0.0, min(100.0, float(target_soc)))
            self._state["battery_soc"] = round(soc, 2)
            self._state["battery_energy_kwh"] = round((soc / 100.0) * self.capacity_kwh, 4)
            self._save()

def get_energy_state_manager(state_file: Optional[Path] = None) -> EnergyStateManager:
    return EnergyStateManager(state_file=state_file)
