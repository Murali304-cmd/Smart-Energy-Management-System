import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BATTERY_CAPACITY_KWH, BATTERY_MIN_SOC, BATTERY_MAX_SOC
from energy.battery_manager import BatteryManager
from energy.backup_calculator import BackupCalculator
from energy.energy_flow import EnergyFlowManager
from energy.energy_state import EnergyStateManager
from server import app

client = TestClient(app)

def test_battery_manager_charging_and_max_soc():
    mgr = BatteryManager(capacity_kwh=10.0, min_soc=20.0, max_soc=90.0, max_charge_kw=3.5, charge_efficiency=0.95)
    # Starting at 80% (8.0 kWh), max allowed is 90% (9.0 kWh) -> headroom is 1.0 kWh
    charge_power, new_soc, new_energy = mgr.charge(
        available_excess_kw=5.0,  # exceeds max_charge_kw (3.5 kW)
        current_energy_kwh=8.0,
        dt_hours=0.5
    )
    assert charge_power <= 3.5
    assert new_soc <= 90.0
    assert new_energy <= 9.0
    assert new_soc > 80.0

def test_battery_manager_discharging_and_min_soc():
    mgr = BatteryManager(capacity_kwh=10.0, min_soc=20.0, max_soc=100.0, max_discharge_kw=5.0, discharge_efficiency=0.95)
    # Starting at 22% (2.2 kWh), min allowed is 20% (2.0 kWh) -> usable is only 0.2 kWh
    discharge_power, new_soc, new_energy = mgr.discharge(
        requested_deficit_kw=4.0,
        current_energy_kwh=2.2,
        dt_hours=0.25
    )
    assert new_soc >= 20.0
    assert new_energy >= 2.0
    # Starting at 20.0% (at min SOC) -> cannot discharge anything
    power_zero, soc_stay, energy_stay = mgr.discharge(
        requested_deficit_kw=2.0,
        current_energy_kwh=2.0,
        dt_hours=0.25
    )
    assert power_zero == 0.0
    assert soc_stay == 20.0

def test_exact_energy_balance_surplus():
    flow = EnergyFlowManager(capacity_kwh=10.0, min_soc=20.0, max_soc=100.0)
    # Solar = 6.0 kW, Load = 3.0 kW -> excess = 3.0 kW to battery
    res = flow.process_realtime_flow(solar_generation_kw=6.0, household_demand_kw=3.0, current_soc=50.0)
    assert res["solar_power_kw"] == 6.0
    assert res["household_load_kw"] == 3.0
    assert res["grid_power_kw"] == 0.0
    assert res["battery_mode"] == "charging"
    assert res["energy_balance_valid"] is True
    # Validate equation: Solar + Battery_Discharge + Grid == Load + Battery_Charge + Export
    supply = res["solar_power_kw"] + (res["battery_power_kw"] if res["battery_mode"] == "discharging" else 0.0) + res["grid_power_kw"]
    demand = res["household_load_kw"] + (res["battery_power_kw"] if res["battery_mode"] == "charging" else 0.0) + res["grid_export_kw"]
    assert abs(supply - demand) < 1e-3

def test_exact_energy_balance_deficit():
    flow = EnergyFlowManager(capacity_kwh=10.0, min_soc=20.0, max_soc=100.0)
    # Solar = 1.0 kW, Load = 5.0 kW, SOC = 20.0% (empty) -> Battery cannot discharge -> Grid supplies 4.0 kW
    res = flow.process_realtime_flow(solar_generation_kw=1.0, household_demand_kw=5.0, current_soc=20.0)
    assert res["solar_power_kw"] == 1.0
    assert res["household_load_kw"] == 5.0
    assert res["battery_power_kw"] == 0.0
    assert res["grid_power_kw"] == 4.0
    assert res["energy_balance_valid"] is True

def test_dynamic_10_hour_backup_calculation():
    calc = BackupCalculator(capacity_kwh=10.0, min_soc=20.0, max_soc=100.0, discharge_efficiency=0.95)
    # Required capacity for 2 kW average load and 10 hours backup:
    # Usable energy required = 2.0 * 10 = 20 kWh
    # Nominal capacity = 20 / (0.8 * 0.95) = 26.3 kWh
    req_cap = calc.calculate_required_capacity(desired_hours=10.0, avg_load_kw=2.0)
    assert req_cap > 25.0

    # With a 10 kWh battery at 50% SOC (3 kWh usable):
    metrics = calc.calculate_backup_metrics(current_soc=50.0, current_load_kw=2.0)
    # Deliverable energy = 3 * 0.95 = 2.85 kWh -> estimated backup hours = 2.85 / 2 = 1.4 hours
    # The system must NEVER falsely return 10 hours
    assert metrics["estimated_backup_hours"] < 5.0
    assert metrics["backup_target_satisfied"] is False
    assert metrics["required_backup_hours"] == 10.0

def test_api_energy_flow_endpoint():
    response = client.get("/api/energy-flow?solar_kw=5.0&load_kw=2.0&battery_soc=70.0")
    assert response.status_code == 200
    data = response.json()
    assert "solar_power_kw" in data
    assert "household_load_kw" in data
    assert "battery_power_kw" in data
    assert "battery_soc" in data
    assert "battery_mode" in data
    assert "estimated_backup_hours" in data
    assert "required_backup_hours" in data
    assert data["required_backup_hours"] == 10.0
    assert data["energy_balance_valid"] is True

def test_api_daily_summary_and_notify():
    sum_resp = client.get("/api/summary/daily?budget=30.0")
    assert sum_resp.status_code == 200
    s_data = sum_resp.json()
    assert s_data["status"] == "success"
    assert "solar_kwh" in s_data
    assert "clean_energy_percentage" in s_data

    notify_resp = client.post("/api/summary/daily/notify", json={"user_budget": 30.0})
    assert notify_resp.status_code == 200
    n_data = notify_resp.json()
    assert n_data["status"] == "success"

def test_api_hourly_notify():
    h_resp = client.post("/api/notifications/hourly-trigger")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "success"
