import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from energy.energy_manager import EnergyManager, get_energy_manager
from energy.energy_allocator import EnergyAllocator, EnergyAllocationError
from energy.cost_optimizer import CostOptimizer
from energy.battery_manager import BatteryManager
from energy.backup_calculator import BackupCalculator
from server import app

client = TestClient(app)

def test_energy_allocator_solar_surplus_and_export():
    """
    Solar = 8 kW, Load = 3 kW
    Solar -> Load = 3 kW
    Excess Solar = 5 kW
    Battery max charge = 3.5 kW
    Remaining 1.5 kW exported to Grid
    """
    allocator = EnergyAllocator(
        capacity_kwh=10.0,
        min_soc=20.0,
        max_soc=100.0,
        max_charge_kw=3.5,
        charge_efficiency=0.95
    )
    res = allocator.allocate(
        solar_generation_kw=8.0,
        household_demand_kw=3.0,
        battery_soc=50.0,
        dt_hours=0.25
    )
    assert res["solar_power_kw"] == 8.0
    assert res["solar_to_load_kw"] == 3.0
    assert res["household_load_kw"] == 3.0
    assert res["battery_charge_kw"] == 3.5
    assert res["grid_export_kw"] == 1.5
    assert res["grid_power_kw"] == 0.0
    assert res["battery_mode"] == "charging"
    assert res["energy_balance_valid"] is True
    # Supply = Demand + Storage + Export
    assert abs((8.0 + 0.0 + 0.0) - (3.0 + 3.5 + 1.5)) < 1e-3

def test_energy_allocator_solar_deficit_battery_sufficient():
    """
    Solar = 2 kW, Load = 5 kW
    Solar -> Load = 2 kW
    Remaining demand = 3 kW
    Battery has sufficient energy -> Battery supplies 3 kW
    Grid = 0 kW
    """
    allocator = EnergyAllocator(
        capacity_kwh=10.0,
        min_soc=20.0,
        max_soc=100.0,
        max_discharge_kw=5.0,
        discharge_efficiency=0.95
    )
    res = allocator.allocate(
        solar_generation_kw=2.0,
        household_demand_kw=5.0,
        battery_soc=70.0,
        dt_hours=0.25
    )
    assert res["solar_to_load_kw"] == 2.0
    assert res["battery_discharge_kw"] == 3.0
    assert res["grid_power_kw"] == 0.0
    assert res["battery_mode"] == "discharging"
    assert res["energy_strategy"] == "SOLAR + BATTERY"
    assert res["energy_balance_valid"] is True

def test_energy_allocator_solar_deficit_grid_backup():
    """
    Solar = 1 kW, Load = 5 kW, Battery at min_soc (20%)
    Solar -> Load = 1 kW
    Battery cannot discharge below min_soc -> 0 kW
    Grid supplies remaining 4 kW
    """
    allocator = EnergyAllocator(
        capacity_kwh=10.0,
        min_soc=20.0,
        max_soc=100.0,
        max_discharge_kw=5.0
    )
    res = allocator.allocate(
        solar_generation_kw=1.0,
        household_demand_kw=5.0,
        battery_soc=20.0,
        dt_hours=0.25
    )
    assert res["solar_to_load_kw"] == 1.0
    assert res["battery_discharge_kw"] == 0.0
    assert res["grid_power_kw"] == 4.0
    assert res["battery_soc_after"] == 20.0
    assert res["energy_strategy"] == "SOLAR + GRID"
    assert res["energy_balance_valid"] is True

def test_energy_allocator_hybrid_all_three():
    """
    Solar = 2 kW, Load = 6 kW, Battery has only 1 kW deliverable power
    Solar = 2 kW, Battery = 1 kW, Grid = 3 kW
    Strategy: SOLAR + BATTERY + GRID
    """
    allocator = EnergyAllocator(
        capacity_kwh=10.0,
        min_soc=20.0,
        max_soc=100.0,
        max_discharge_kw=1.0  # Force limit to 1.0 kW
    )
    res = allocator.allocate(
        solar_generation_kw=2.0,
        household_demand_kw=6.0,
        battery_soc=50.0,
        dt_hours=0.25
    )
    assert res["solar_to_load_kw"] == 2.0
    assert res["battery_discharge_kw"] == 1.0
    assert res["grid_power_kw"] == 3.0
    assert res["energy_strategy"] == "SOLAR + BATTERY + GRID"
    assert res["energy_balance_valid"] is True

def test_cost_optimizer_within_and_exceeded_budget():
    optimizer = CostOptimizer(default_budget=25.0)
    # 2 kW grid for 1 hour at ₹5/kWh = ₹10 <= ₹25 -> Within Budget
    res_within = optimizer.evaluate_budget(estimated_cost=10.0, user_budget=25.0)
    assert res_within["budget_status"] == "Within Budget"
    assert res_within["budget_exceeded"] is False

    # 6 kW grid for 1 hour at ₹5/kWh = ₹30 > ₹25 -> Budget Exceeded
    res_over = optimizer.evaluate_budget(estimated_cost=30.0, user_budget=25.0)
    assert res_over["budget_status"] == "Budget Exceeded"
    assert res_over["budget_exceeded"] is True
    assert "cannot be achieved" in res_over["message"]

def test_10_hour_backup_calculator_true_duration():
    calc = BackupCalculator(capacity_kwh=10.0, min_soc=20.0, max_soc=100.0, discharge_efficiency=0.95)
    # At 50% SOC, usable energy = 3 kWh * 0.95 = 2.85 kWh
    # Under 2 kW load, backup duration = 1.4 hours -> must NOT be 10 hours
    metrics_low = calc.calculate_backup_metrics(current_soc=50.0, current_load_kw=2.0)
    assert metrics_low["estimated_backup_hours"] < 5.0
    assert metrics_low["backup_status"].lower() == "10-hour backup not available"
    assert metrics_low["backup_target_satisfied"] is False

    # With a 30 kWh battery at 90% SOC (21 kWh usable deliverable) under 1 kW load = ~20 hours
    metrics_high = calc.calculate_backup_metrics(current_soc=90.0, current_load_kw=1.0, battery_capacity_kwh=30.0)
    assert metrics_high["estimated_backup_hours"] >= 10.0
    assert metrics_high["backup_status"].lower() == "10-hour backup available"
    assert metrics_high["backup_target_satisfied"] is True

def test_energy_manager_process_energy_decision():
    mgr = EnergyManager()
    output = mgr.process_energy_decision(
        predicted_solar=4.5,
        household_demand=3.0,
        predicted_price=4.70,
        battery_soc=60.0,
        user_budget=20.0
    )
    # Standard output schema fields check
    assert "solar_power_kw" in output
    assert "household_load_kw" in output
    assert "battery_power_kw" in output
    assert "battery_mode" in output
    assert "battery_soc_before" in output
    assert "battery_soc_after" in output
    assert "grid_power_kw" in output
    assert "grid_export_kw" in output
    assert "estimated_cost" in output
    assert "user_budget" in output
    assert "budget_status" in output
    assert "available_battery_energy_kwh" in output
    assert "estimated_backup_hours" in output
    assert output["required_backup_hours"] == 10
    assert "backup_status" in output
    assert "energy_strategy" in output
    assert output["energy_balance_valid"] is True

def test_api_energy_manage_endpoints():
    # POST endpoint test
    post_res = client.post(
        "/api/energy/manage",
        json={
            "predicted_solar": 5.0,
            "household_demand": 2.5,
            "predicted_price": 4.5,
            "battery_soc": 70.0,
            "user_budget": 25.0
        }
    )
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["solar_power_kw"] == 5.0
    assert data["household_load_kw"] == 2.5
    assert data["grid_power_kw"] == 0.0
    assert data["battery_mode"] == "charging"
    assert data["required_backup_hours"] == 10
    assert data["energy_balance_valid"] is True

    # GET endpoint test
    get_res = client.get("/api/energy/manage?predicted_solar=3.0&household_demand=4.0&predicted_price=4.8")
    assert get_res.status_code == 200
    g_data = get_res.json()
    assert g_data["household_load_kw"] == 4.0
    assert g_data["energy_balance_valid"] is True

def test_api_energy_management_server_route():
    res = client.get("/api/energy-management")
    assert res.status_code == 200
    data = res.json()
    assert "solar_power_kw" in data
    assert "energy_balance_valid" in data
    assert data["required_backup_hours"] == 10
