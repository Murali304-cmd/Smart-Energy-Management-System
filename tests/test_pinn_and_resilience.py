"""
Unit tests for SEMS Enterprise v3.0 Upgrades:
1. Physics-Informed Neural Network (PINN) battery electrochemical ODE checks.
2. Islanding Controller fault detection & state transitions.
3. Multi-Agent Swarm double-auction clearing & Proof-of-Green ledger.
4. OpenADR 2.0b Demand Response & Fast Frequency Response (FFR).
"""

import pytest
import torch
from prediction.pinn_battery_model import BatteryPINN, PhysicsInformedBatteryEngine
from services.islanding_controller import IslandingController, GridOperatingMode
from services.multi_agent_swarm import MultiAgentSwarmEngine
from services.demand_response_ven import DemandResponseVEN

def test_pinn_model_forward_and_physics_loss():
    model = BatteryPINN()
    inputs = torch.tensor([[0.75, 20.0, 298.15, 0.05, 0.2]], dtype=torch.float32)
    preds = model(inputs)
    assert preds.shape == (1, 3) # [Voltage, Temp, R_int]
    
    loss = model.compute_physics_loss(inputs, preds)
    assert isinstance(loss.item(), float)
    assert not torch.isnan(loss)

def test_pinn_engine_evaluation():
    engine = PhysicsInformedBatteryEngine()
    res = engine.evaluate_cell_physics(
        soc_percent=70.0,
        current_charge_kw=3.5,
        current_discharge_kw=0.0,
        ambient_temp_c=28.0,
        cycle_count=150
    )
    assert res["status"] == "success"
    pinn = res["pinn_state"]
    assert 46.0 <= pinn["terminal_voltage_v"] <= 58.0
    assert pinn["cell_temperature_c"] >= 28.0
    assert 70.0 <= pinn["soh_percent"] <= 100.0
    assert pinn["physics_verified"] is True

def test_islanding_controller_disconnect_and_restore():
    controller = IslandingController()
    assert controller.mode == GridOperatingMode.GRID_TIED

    # Trigger Disconnect
    event = controller.trigger_grid_disconnect("TEST_GRID_FAULT")
    assert controller.mode == GridOperatingMode.ISLANDED_AUTONOMOUS
    assert event["transition_time_ms"] < 20.0 # Sub-cycle latency

    # Restore Connection
    rec_event = controller.restore_grid_connection()
    assert controller.mode == GridOperatingMode.GRID_TIED
    assert rec_event["pll_lock_achieved"] is True

def test_islanding_controller_telemetry_evaluation():
    controller = IslandingController()
    # Abnormal low voltage (< 195.5V) should trigger islanding
    status = controller.evaluate_telemetry(grid_voltage=180.0, grid_frequency=50.0, battery_soc=80.0, current_load_kw=2.0)
    assert status["mode"] == GridOperatingMode.ISLANDED_AUTONOMOUS
    assert status["grid_healthy"] is False

def test_multi_agent_swarm_market_clearing():
    engine = MultiAgentSwarmEngine()
    res = engine.run_swarm_market_clearing(
        local_solar_kw=4.5,
        local_load_kw=1.5, # 3.0 kW surplus
        local_soc=85.0,
        grid_import_tariff=5.00,
        grid_export_feedin=2.50
    )
    assert res["status"] == "success"
    assert res["market_clearing_inr"] == 3.75 # Midpoint (5.00 + 2.50) / 2
    assert len(res["active_swarm_nodes"]) == 4
    assert len(res["proof_of_green_ledger"]) > 0

def test_demand_response_ven_and_ffr():
    ven = DemandResponseVEN()
    status = ven.get_demand_response_status()
    assert status["status"] == "success"
    assert status["vtn_connection"] == "CONNECTED"

    # Fast Frequency Response under-frequency test (e.g. 49.90 Hz)
    ffr_under = ven.process_fast_frequency_response(49.90)
    assert ffr_under["ffr_active"] is True
    assert ffr_under["response_type"] == "INJECT_POWER_UNDERFREQ"
    assert ffr_under["recommended_bess_setpoint_kw"] > 0.0

    # Over-frequency test (e.g. 50.10 Hz)
    ffr_over = ven.process_fast_frequency_response(50.10)
    assert ffr_over["ffr_active"] is True
    assert ffr_over["response_type"] == "ABSORB_POWER_OVERFREQ"
    assert ffr_over["recommended_bess_setpoint_kw"] < 0.0
