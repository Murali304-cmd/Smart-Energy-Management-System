import os
import json
import random
import logging
from collections import deque
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Union
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

try:
    from config.settings import (
        DQN_LEARNING_RATE,
        DQN_GAMMA,
        DQN_EPSILON_START,
        DQN_EPSILON_MIN,
        DQN_EPSILON_DECAY,
        DQN_BATCH_SIZE,
        DQN_MEMORY_SIZE,
        DQN_TARGET_UPDATE_FREQ,
        DQN_MODEL_PATH
    )
except ImportError:
    DQN_LEARNING_RATE = 0.001
    DQN_GAMMA = 0.95
    DQN_EPSILON_START = 1.0
    DQN_EPSILON_MIN = 0.05
    DQN_EPSILON_DECAY = 0.995
    DQN_BATCH_SIZE = 64
    DQN_MEMORY_SIZE = 10000
    DQN_TARGET_UPDATE_FREQ = 10
    DQN_MODEL_PATH = Path(__file__).resolve().parent.parent / "trained_models" / "dqn_energy_recommender.pth"

from recommendation.environment import STATE_DIM, ACTION_DIM, ACTION_NAMES

logger = logging.getLogger("SEMS.DQNModel")

class StateScaler:
    def __init__(self, feature_ranges: Optional[Dict[str, Tuple[float, float]]] = None):
        self.feature_ranges = feature_ranges or {
            "predicted_solar": (0.0, 8.0),
            "predicted_load": (0.0, 8.0),
            "electricity_price": (0.0, 15.0),
            "battery_soc": (0.0, 100.0),
            "current_load": (0.0, 8.0),
            "time_peak_indicator": (0.0, 1.0)
        }
        self.keys = [
            "predicted_solar",
            "predicted_load",
            "electricity_price",
            "battery_soc",
            "current_load",
            "time_peak_indicator"
        ]

    def transform(self, state: Union[np.ndarray, List[float]]) -> np.ndarray:
        s = np.array(state, dtype=np.float32)
        scaled = np.zeros_like(s)
        for i, key in enumerate(self.keys[:len(s)]):
            min_val, max_val = self.feature_ranges.get(key, (0.0, 1.0))
            span = max(1e-5, max_val - min_val)
            scaled[i] = (s[i] - min_val) / span
        return np.clip(scaled, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {"feature_ranges": {k: list(v) for k, v in self.feature_ranges.items()}}

    def save_config(self, filepath: Union[str, Path]):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_config(cls, filepath: Union[str, Path]) -> "StateScaler":
        path = Path(filepath)
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ranges = {k: tuple(v) for k, v in data.get("feature_ranges", {}).items()}
        return cls(feature_ranges=ranges)

class DQNNetwork(nn.Module):
    def __init__(self, state_dim: int = STATE_DIM, action_dim: int = ACTION_DIM, hidden_dim: int = 64):
        super(DQNNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)

class ReplayBuffer:
    def __init__(self, capacity: int = DQN_MEMORY_SIZE):
        self.buffer = deque(maxlen=capacity)

    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int = DQN_BATCH_SIZE) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.tensor(np.array(states), dtype=torch.float32),
            torch.tensor(actions, dtype=torch.int64),
            torch.tensor(rewards, dtype=torch.float32),
            torch.tensor(np.array(next_states), dtype=torch.float32),
            torch.tensor(dones, dtype=torch.float32)
        )

    def __len__(self) -> int:
        return len(self.buffer)

class DQNAgent:
    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = ACTION_DIM,
        hidden_dim: int = 64,
        learning_rate: float = DQN_LEARNING_RATE,
        gamma: float = DQN_GAMMA,
        epsilon: float = DQN_EPSILON_START,
        epsilon_min: float = DQN_EPSILON_MIN,
        epsilon_decay: float = DQN_EPSILON_DECAY,
        batch_size: int = DQN_BATCH_SIZE,
        memory_size: int = DQN_MEMORY_SIZE,
        target_update_freq: int = DQN_TARGET_UPDATE_FREQ,
        scaler: Optional[StateScaler] = None,
        device: Optional[torch.device] = None
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.scaler = scaler or StateScaler()
        self.device = device or torch.device("cpu")

        self.policy_net = DQNNetwork(state_dim, action_dim, hidden_dim).to(self.device)
        self.target_net = DQNNetwork(state_dim, action_dim, hidden_dim).to(self.device)
        self.update_target_network()
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)
        self.criterion = nn.SmoothL1Loss()
        self.memory = ReplayBuffer(capacity=memory_size)
        self.replay_buffer = self.memory
        self.train_step_count = 0
        self.is_trained = False

    def update_target_network(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def select_action(self, state: Union[np.ndarray, List[float]], eval_mode: bool = False) -> Tuple[int, List[float]]:
        if isinstance(state, list):
            state = np.array(state, dtype=np.float32)
        scaled_state = self.scaler.transform(state)
        state_tensor = torch.tensor(scaled_state, dtype=torch.float32).unsqueeze(0).to(self.device)

        self.policy_net.eval()
        with torch.no_grad():
            q_values_tensor = self.policy_net(state_tensor)
            q_values = q_values_tensor.cpu().squeeze(0).tolist()
            q_values = [round(float(q), 4) for q in q_values]

        if not eval_mode and random.random() < self.epsilon:
            action = random.randint(0, self.action_dim - 1)
        else:
            action = int(np.argmax(q_values))
        return (action, q_values)

    def train_step(self) -> Optional[float]:
        if len(self.memory) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        scaled_states = torch.tensor(
            np.array([self.scaler.transform(s.numpy()) for s in states]),
            dtype=torch.float32
        ).to(self.device)
        scaled_next_states = torch.tensor(
            np.array([self.scaler.transform(ns.numpy()) for ns in next_states]),
            dtype=torch.float32
        ).to(self.device)

        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        dones = dones.to(self.device)

        self.policy_net.train()
        curr_q = self.policy_net(scaled_states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            max_next_q = self.target_net(scaled_next_states).max(1)[0]
            target_q = rewards + (self.gamma * max_next_q * (1.0 - dones))

        loss = self.criterion(curr_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=5.0)
        self.optimizer.step()

        self.train_step_count += 1
        if self.train_step_count % self.target_update_freq == 0:
            self.update_target_network()

        if self.epsilon > self.epsilon_min:
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        return float(loss.item())

    def save(self, filepath: Union[str, Path] = DQN_MODEL_PATH):
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "policy_net_state_dict": self.policy_net.state_dict(),
            "target_net_state_dict": self.target_net.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "epsilon": self.epsilon,
            "gamma": self.gamma,
            "learning_rate": self.learning_rate,
            "scaler_config": self.scaler.to_dict()
        }, filepath)
        scaler_path = filepath.parent / "dqn_scaler_config.json"
        self.scaler.save_config(scaler_path)
        self.is_trained = True
        logger.info(f"DQN recommendation model saved to {filepath}")

    def load(self, filepath: Union[str, Path] = DQN_MODEL_PATH):
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"DQN model weights not found at {filepath}")
        checkpoint = torch.load(filepath, map_location=self.device)
        self.state_dim = checkpoint.get("state_dim", STATE_DIM)
        self.action_dim = checkpoint.get("action_dim", ACTION_DIM)
        self.hidden_dim = checkpoint.get("hidden_dim", 64)
        
        self.policy_net = DQNNetwork(self.state_dim, self.action_dim, self.hidden_dim).to(self.device)
        self.target_net = DQNNetwork(self.state_dim, self.action_dim, self.hidden_dim).to(self.device)
        self.policy_net.load_state_dict(checkpoint["policy_net_state_dict"])
        self.target_net.load_state_dict(checkpoint["target_net_state_dict"])
        self.policy_net.eval()
        self.target_net.eval()

        if "scaler_config" in checkpoint:
            ranges = {k: tuple(v) for k, v in checkpoint["scaler_config"].get("feature_ranges", {}).items()}
            self.scaler = StateScaler(feature_ranges=ranges)
        self.is_trained = True
        logger.info(f"DQN recommendation model loaded from {filepath}")
