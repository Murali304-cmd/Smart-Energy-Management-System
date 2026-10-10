import sys
from pathlib import Path
import pytest
import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BATTERY_MIN_SOC, BATTERY_CAPACITY_KWH, DQN_MODEL_PATH
from recommendation.allocation import BatteryConfig, allocate_energy
from recommendation.environment import (
    EnergyManagementEnv,
    calculate_reward,
    ACTION_PRIORITY_HYBRID,
    ACTION_NAMES,
    STATE_DIM,
    ACTION_DIM
)
from recommendation.dqn_model import DQNNetwork, DQNAgent, ReplayBuffer, StateScaler
from recommendation.recommender import EnergyRecommenderService, recommend_energy

def test_environment_initialization_and_reset():
    env = EnergyManagementEnv()
    initial_state = {
        "predicted_solar": 2.5,
        "predicted_load": 1.8,
        "predicted_price": 4.7,
        "battery_soc": 75.0,
        "user_demand": 1.8,
        "user_budget": 100.0
    }
    state = env.reset(initial_state)
    assert isinstance(state, np.ndarray)
    assert len(state) == 6
    assert state[0] == 2.5
    assert state[3] == 75.0
    assert state[5] == 100.0

def test_dqn_network_architecture_and_q_values():
    net = DQNNetwork(state_dim=6, action_dim=4, hidden_dim=64)
    dummy_state = torch.tensor([[2.5, 1.8, 4.7, 70.0, 1.8, 100.0]], dtype=torch.float32)
    q_out = net(dummy_state)
    assert q_out.shape == (1, 4)
    assert not torch.isnan(q_out).any()

def test_replay_buffer_push_and_sample():
    buffer = ReplayBuffer(capacity=100)
    s = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 100.0])
    s_next = np.array([1.1, 2.1, 3.1, 4.1, 5.1, 100.0])
    for _ in range(20):
        buffer.push(s, 0, 1.5, s_next, False)
    assert len(buffer) == 20
    states, actions, rewards, next_states, dones = buffer.sample(batch_size=8)
    assert states.shape == (8, 6)
    assert actions.shape == (8,)
    assert rewards.shape == (8,)

def test_state_scaler_transform_and_config():
    scaler = StateScaler()
    raw_state = [5.0, 5.0, 10.0, 50.0, 5.0, 250.0]
    scaled = scaler.transform(raw_state)
    assert len(scaled) == 6
    assert np.all(scaled >= 0.0) and np.all(scaled <= 1.0)
    assert round(float(scaled[3]), 2) == 0.50

def test_1_high_solar_low_demand():
    payload = {
        "predicted_solar": 6.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc": 50.0,
        "user_demand": 5.0,
        "user_budget": 100.0
    }
    res = recommend_energy(payload)
    assert res["status"] == "success"
    assert res["recommended_strategy"] == "SOLAR ONLY"
    assert res["solar_power"] == 5.0
    assert res["battery_power"] == 0.0
    assert res["grid_power"] == 0.0
    assert res["grid_usage"] == "none"

def test_2_solar_partially_satisfies_demand_sufficient_battery():
    payload = {
        "predicted_solar": 2.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc": 80.0,
        "user_demand": 5.0,
        "user_budget": 100.0
    }
    res = recommend_energy(payload)
    assert res["status"] == "success"
    assert res["recommended_strategy"] == "SOLAR + BATTERY"
    assert res["solar_power"] == 2.0
    assert res["battery_power"] == 3.0
    assert res["grid_power"] == 0.0
    assert res["grid_usage"] == "none"

def test_3_solar_and_battery_insufficient():
    payload = {
        "predicted_solar": 4.0,
        "predicted_load": 6.0,
        "predicted_price": 4.7,
        "battery_soc": 21.0,
        "user_demand": 6.0,
        "user_budget": 100.0
    }
    cfg = BatteryConfig(capacity_kwh=10.0, min_soc=20.0, discharge_efficiency=1.0, dt_hours=0.25)
    alloc = allocate_energy(4.0, 23.75, 6.0, 100.0, 4.7, battery_config=cfg)
    assert alloc["solar_power"] == 4.0
    assert alloc["battery_power"] == 1.5
    assert alloc["grid_power"] == 0.5
    assert alloc["recommended_strategy"] == "SOLAR + BATTERY + GRID"
    
    res = recommend_energy(payload)
    assert res["status"] == "success"
    assert res["solar_power"] == 4.0
    assert res["battery_power"] > 0.0
    assert res["grid_power"] > 0.0
    assert "GRID" in res["recommended_strategy"]

def test_4_no_solar_sufficient_battery():
    payload = {
        "predicted_solar": 0.0,
        "predicted_load": 3.0,
        "predicted_price": 4.7,
        "battery_soc": 80.0,
        "user_demand": 3.0,
        "user_budget": 100.0
    }
    res = recommend_energy(payload)
    assert res["status"] == "success"
    assert res["recommended_strategy"] == "BATTERY ONLY"
    assert res["solar_power"] == 0.0
    assert res["battery_power"] == 3.0
    assert res["grid_power"] == 0.0

def test_5_no_solar_insufficient_battery():
    payload = {
        "predicted_solar": 0.0,
        "predicted_load": 5.0,
        "predicted_price": 4.7,
        "battery_soc": 25.0,
        "user_demand": 5.0,
        "user_budget": 100.0
    }
    res = recommend_energy(payload)
    assert res["status"] == "success"
    assert res["recommended_strategy"] == "BATTERY + GRID"
    assert res["solar_power"] == 0.0
    assert res["battery_power"] > 0.0
    assert res["grid_power"] > 0.0

def test_6_high_electricity_cost_minimizes_grid():
    payload_normal = {
        "predicted_solar": 1.0,
        "predicted_load": 3.0,
        "predicted_price": 4.0,
        "battery_soc": 70.0,
        "user_demand": 3.0,
        "user_budget": 100.0
    }
    res_normal = recommend_energy(payload_normal)
    assert res_normal["grid_power"] == 0.0
    
    payload_high = {
        "predicted_solar": 1.0,
        "predicted_load": 3.0,
        "predicted_price": 12.0,
        "battery_soc": 70.0,
        "user_demand": 3.0,
        "user_budget": 100.0
    }
    res_high = recommend_energy(payload_high)
    assert res_high["grid_power"] == 0.0
    assert res_high["solar_power"] == 1.0
    assert res_high["battery_power"] == 2.0

def test_7_low_user_budget_flags_status():
    payload_within = {
        "predicted_solar": 0.0,
        "predicted_load": 4.0,
        "predicted_price": 5.0,
        "battery_soc": 10.0,
        "user_demand": 4.0,
        "user_budget": 50.0
    }
    res_within = recommend_energy(payload_within)
    assert res_within["status"] == "success"
    assert res_within["budget_status"] == "within_budget"

    payload_over = {
        "predicted_solar": 0.0,
        "predicted_load": 4.0,
        "predicted_price": 5.0,
        "battery_soc": 10.0,
        "user_demand": 4.0,
        "user_budget": 1.0
    }
    res_over = recommend_energy(payload_over)
    assert res_over["status"] == "success"
    assert res_over["budget_status"] == "over_budget"

def test_8_battery_soc_near_minimum_restricts_discharge():
    payload = {
        "predicted_solar": 0.0,
        "predicted_load": 3.0,
        "predicted_price": 4.7,
        "battery_soc": 20.0,
        "user_demand": 3.0,
        "user_budget": 100.0
    }
    res = recommend_energy(payload)
    assert res["status"] == "success"
    assert res["battery_power"] == 0.0
    assert res["grid_power"] == 3.0
    assert res["recommended_strategy"] == "GRID BACKUP"
    assert res["battery_soc_after"] == 20.0

def test_9_invalid_and_missing_inputs_rejected():
    incomplete = {"predicted_solar": 2.5, "battery_soc": 50.0}
    res_inc = recommend_energy(incomplete)
    assert res_inc["status"] == "error"
    assert "Missing required prediction input(s)" in res_inc["error"]
    assert "predicted_load" in res_inc["missing_fields"]
    assert "predicted_price" in res_inc["missing_fields"]

    invalid_solar = {
        "predicted_solar": -1.0,
        "predicted_load": 2.0,
        "predicted_price": 4.7,
        "battery_soc": 50.0,
        "user_demand": 2.0
    }
    res_solar = recommend_energy(invalid_solar)
    assert res_solar["status"] == "error"
    assert "predicted_solar" in res_solar["error"]

    invalid_demand = {
        "predicted_solar": 2.0,
        "predicted_load": 2.0,
        "predicted_price": 4.7,
        "battery_soc": 50.0,
        "user_demand": -5.0
    }
    res_demand = recommend_energy(invalid_demand)
    assert res_demand["status"] == "error"
    assert "user_demand" in res_demand["error"]

def test_10_energy_balance_across_scenarios():
    test_cases = [
        {"predicted_solar": 5.0, "predicted_load": 3.0, "predicted_price": 4.7, "battery_soc": 70.0, "user_demand": 3.0},
        {"predicted_solar": 2.0, "predicted_load": 6.0, "predicted_price": 4.7, "battery_soc": 80.0, "user_demand": 6.0},
        {"predicted_solar": 1.0, "predicted_load": 5.0, "predicted_price": 4.7, "battery_soc": 25.0, "user_demand": 5.0},
        {"predicted_solar": 0.0, "predicted_load": 4.0, "predicted_price": 4.7, "battery_soc": 15.0, "user_demand": 4.0},
        {"predicted_solar": 4.0, "predicted_load": 6.0, "predicted_price": 4.7, "battery_soc": 23.75, "user_demand": 6.0}
    ]
    for case in test_cases:
        res = recommend_energy(case)
        assert res["status"] == "success"
        demand = res["user_demand"]
        total = res["solar_power"] + res["battery_power"] + res["grid_power"]
        assert abs(total - demand) < 1e-4
        assert abs(res["total_power"] - demand) < 1e-4
