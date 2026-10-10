"""
Unit and Integration Tests for BatteryManager and 10-Hour Backup Calculator
"""

import pytest
from energy.battery_manager import BatteryManager
from energy.backup_calculator import BackupCalculator
from energy.energy_allocator import EnergyAllocator, EnergyAllocationError


def test_battery_manager_soc_validation():
    """Validates SOC range clamping and validation."""
    bm = BatteryManager(capacity_kwh=20.0, min_soc=20.0, max_soc=100.0)

    assert bm.validate_soc(50.0) == 50.0
    assert bm.validate_soc(0.0) == 0.0
    assert bm.validate_soc(100.0) == 100.0
    assert bm.validate_soc(-5.0) is None
    assert bm.validate_soc(105.0) is None
    assert bm.validate_soc("invalid") is None
    assert bm.validate_soc(None) is None


def test_battery_manager_energy_calculations():
    """Validates stored available energy and usable deliverable energy."""
    bm = BatteryManager(
        capacity_kwh=20.0,
        min_soc=20.0,
        max_soc=100.0,
        discharge_efficiency=0.95
    )

    # At 70% SOC: usable SOC fraction is (70 - 20) / 100 = 0.50
    # Available energy in cells = 20.0 * 0.50 = 10.0 kWh
    avail = bm.calculate_available_energy(current_soc=70.0)
    assert avail == 10.0

    # Usable deliverable energy = 10.0 * 0.95 = 9.5 kWh
    usable = bm.calculate_usable_energy(current_soc=70.0)
    assert usable == 9.5

    # At or below min SOC (<= 20%): available energy should be 0.0
    assert bm.calculate_available_energy(current_soc=20.0) == 0.0
    assert bm.calculate_usable_energy(current_soc=15.0) == 0.0


def test_10_hour_backup_calculator_dynamic_computation():
    """Tests dynamic 10-hour backup requirement calculation without hardcoding."""
    calc = BackupCalculator(
        capacity_kwh=20.0,
        min_soc=20.0,
        max_soc=100.0,
        discharge_efficiency=0.95,
        default_desired_backup_hours=10.0,
        default_avg_load_kw=2.0
    )

    # Case A: High SOC (80%), Low Load (1.0 kW) -> Backup should exceed 10 hours
    # Usable energy = 20 * (80 - 20)/100 * 0.95 = 11.4 kWh
    # Backup hours = 11.4 / 1.0 = 11.4 hours (>= 10)
    metrics_a = calc.calculate_backup_metrics(current_soc=80.0, current_load_kw=1.0)
    assert metrics_a["estimated_backup_hours"] == 11.4
    assert metrics_a["ten_hour_backup_available"] is True
    assert metrics_a["backup_status"] == "10-hour backup available"
    assert "10-Hour Backup Available" in metrics_a["status_label"]

    # Case B: Low SOC (40%), High Load (3.0 kW) -> Backup should NOT meet 10 hours
    # Usable energy = 20 * (40 - 20)/100 * 0.95 = 3.8 kWh
    # Backup hours = 3.8 / 3.0 = 1.26 ~ 1.3 hours (< 10)
    metrics_b = calc.calculate_backup_metrics(current_soc=40.0, current_load_kw=3.0)
    assert metrics_b["estimated_backup_hours"] < 10.0
    assert metrics_b["ten_hour_backup_available"] is False
    assert metrics_b["backup_status"] == "10-hour backup not available"
    assert "10-Hour Backup Not Available" in metrics_b["status_label"]


def test_energy_allocator_solar_serves_home_first():
    """Case 1: Solar > Home Demand -> Solar serves Home first, excess to Battery."""
    allocator = EnergyAllocator(capacity_kwh=20.0, min_soc=20.0, max_soc=100.0)

    # Solar = 5.0 kW, Demand = 3.0 kW, Battery SOC = 50%
    result = allocator.allocate(
        solar_generation_kw=5.0,
        household_demand_kw=3.0,
        battery_soc=50.0,
        dt_hours=0.25
    )

    assert result["solar_to_load_kw"] == 3.0
    assert result["household_load_kw"] == 3.0
    assert result["battery_charge_kw"] > 0.0  # Excess solar charges battery
    assert result["battery_discharge_kw"] == 0.0
    assert result["grid_power_kw"] == 0.0
    assert result["energy_balance_valid"] is True


def test_energy_allocator_solar_deficit_battery_discharges_first():
    """Case 2: Solar < Home Demand -> Solar serves load, Battery covers deficit, Grid covers remainder."""
    allocator = EnergyAllocator(capacity_kwh=20.0, min_soc=20.0, max_soc=100.0)

    # Solar = 2.0 kW, Demand = 5.0 kW, Battery SOC = 80% (sufficient energy)
    result = allocator.allocate(
        solar_generation_kw=2.0,
        household_demand_kw=5.0,
        battery_soc=80.0,
        dt_hours=0.25
    )

    assert result["solar_to_load_kw"] == 2.0
    assert result["battery_discharge_kw"] == 3.0  # Battery covers remaining 3 kW
    assert result["grid_power_kw"] == 0.0
    assert result["energy_balance_valid"] is True


def test_energy_allocator_energy_balance_supply_equals_demand():
    """Validates exact physical energy balance: Solar + Batt_Discharge + Grid_Import == Load + Batt_Charge + Grid_Export."""
    allocator = EnergyAllocator(capacity_kwh=20.0, min_soc=20.0, max_soc=100.0)

    for solar, load, soc in [
        (6.0, 2.0, 50.0),
        (1.0, 4.0, 80.0),
        (0.0, 5.0, 20.0),  # Battery depleted, full grid
        (8.0, 1.0, 99.0)   # Battery nearly full, grid export
    ]:
        res = allocator.allocate(solar_generation_kw=solar, household_demand_kw=load, battery_soc=soc)
        assert res["energy_balance_valid"] is True
        total_supply = res["solar_power_kw"] + res["battery_discharge_kw"] + res["grid_power_kw"]
        total_demand = res["household_load_kw"] + res["battery_charge_kw"] + res["grid_export_kw"]
        assert abs(total_supply - total_demand) < 1e-2
