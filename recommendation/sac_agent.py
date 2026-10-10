import os
import math
import random
import logging
from collections import deque
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Normal

logger = logging.getLogger("SEMS.SACAgent")

class ValueNetwork(nn.Module):
    """Critic network estimating State-Action Value Q(s, a)."""
    def __init__(self, state_dim: int = 8, action_dim: int = 1, hidden_dim: int = 256):
        super(ValueNetwork, self).__init__()
        self.fc1 = nn.Linear(state_dim + action_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, 64)
        self.fc4 = nn.Linear(64, 1)
        self.layer_norm = nn.LayerNorm(hidden_dim)

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        x = torch.cat([state, action], dim=-1)
        x = F.relu(self.fc1(x))
        x = self.layer_norm(F.relu(self.fc2(x)))
        x = F.relu(self.fc3(x))
        return self.fc4(x)


class GaussianPolicyNetwork(nn.Module):
    """Gaussian Policy Network outputting mean and log_std for continuous action setpoint."""
    def __init__(
        self,
        state_dim: int = 8,
        action_dim: int = 1,
        hidden_dim: int = 256,
        log_std_min: float = -20.0,
        log_std_max: float = 2.0,
        action_scale: float = 5.0
    ):
        super(GaussianPolicyNetwork, self).__init__()
        self.log_std_min = log_std_min
        self.log_std_max = log_std_max
        self.action_scale = action_scale

        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc_mean = nn.Linear(hidden_dim, action_dim)
        self.fc_log_std = nn.Linear(hidden_dim, action_dim)
        self.layer_norm = nn.LayerNorm(hidden_dim)

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = F.relu(self.fc1(state))
        x = self.layer_norm(F.relu(self.fc2(x)))
        mean = self.fc_mean(x)
        log_std = self.fc_log_std(x)
        log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
        return mean, log_std

    def sample(self, state: torch.Tensor, epsilon: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mean, log_std = self.forward(state)
        std = log_std.exp()
        normal = Normal(mean, std)
        z = normal.rsample()
        action = torch.tanh(z) * self.action_scale
        log_prob = normal.log_prob(z) - torch.log(self.action_scale * (1 - torch.tanh(z).pow(2)) + epsilon)
        log_prob = log_prob.sum(dim=-1, keepdim=True)
        mean_action = torch.tanh(mean) * self.action_scale
        return action, log_prob, mean_action


class SACContinuousAgent:
    """
    Continuous Soft Actor-Critic Reinforcement Learning Agent for Micro-Inverter
    and Battery Energy Management with Continuous Power Setpoint and Entropy Regularization.
    """
    def __init__(
        self,
        state_dim: int = 8,
        action_dim: int = 1,
        max_action_kw: float = 5.0,
        gamma: float = 0.99,
        tau: float = 0.005,
        alpha: float = 0.2,
        lr: float = 3e-4,
        memory_size: int = 50000,
        batch_size: int = 128,
        device: str = "cpu"
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.max_action_kw = max_action_kw
        self.gamma = gamma
        self.tau = tau
        self.alpha = alpha
        self.batch_size = batch_size
        self.device = torch.device(device)

        self.policy = GaussianPolicyNetwork(state_dim, action_dim, action_scale=max_action_kw).to(self.device)
        self.policy_optimizer = optim.Adam(self.policy.parameters(), lr=lr)

        self.critic1 = ValueNetwork(state_dim, action_dim).to(self.device)
        self.critic2 = ValueNetwork(state_dim, action_dim).to(self.device)
        self.critic1_target = ValueNetwork(state_dim, action_dim).to(self.device)
        self.critic2_target = ValueNetwork(state_dim, action_dim).to(self.device)

        self.critic1_target.load_state_dict(self.critic1.state_dict())
        self.critic2_target.load_state_dict(self.critic2.state_dict())

        self.critic1_optimizer = optim.Adam(self.critic1.parameters(), lr=lr)
        self.critic2_optimizer = optim.Adam(self.critic2.parameters(), lr=lr)

        self.memory = deque(maxlen=memory_size)
        self.total_steps = 0

    def select_action(self, state: np.ndarray, evaluate: bool = False) -> float:
        state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            if evaluate:
                mean, _ = self.policy(state_t)
                action = torch.tanh(mean) * self.max_action_kw
            else:
                action, _, _ = self.policy.sample(state_t)
        return float(action.cpu().numpy()[0][0])

    def store_transition(self, state: np.ndarray, action: float, reward: float, next_state: np.ndarray, done: bool):
        self.memory.append((state, np.array([action], dtype=np.float32), reward, next_state, done))
        self.total_steps += 1

    def train_step(self) -> Optional[Dict[str, float]]:
        if len(self.memory) < self.batch_size:
            return None

        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states_t = torch.FloatTensor(np.array(states)).to(self.device)
        actions_t = torch.FloatTensor(np.array(actions)).to(self.device)
        rewards_t = torch.FloatTensor(rewards).unsqueeze(1).to(self.device)
        next_states_t = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones_t = torch.FloatTensor(dones).unsqueeze(1).to(self.device)

        with torch.no_grad():
            next_actions, next_log_prob, _ = self.policy.sample(next_states_t)
            target_q1 = self.critic1_target(next_states_t, next_actions)
            target_q2 = self.critic2_target(next_states_t, next_actions)
            target_q = torch.min(target_q1, target_q2) - self.alpha * next_log_prob
            q_target = rewards_t + (1.0 - dones_t) * self.gamma * target_q

        current_q1 = self.critic1(states_t, actions_t)
        current_q2 = self.critic2(states_t, actions_t)
        critic1_loss = F.mse_loss(current_q1, q_target)
        critic2_loss = F.mse_loss(current_q2, q_target)

        self.critic1_optimizer.zero_grad()
        critic1_loss.backward()
        self.critic1_optimizer.step()

        self.critic2_optimizer.zero_grad()
        critic2_loss.backward()
        self.critic2_optimizer.step()

        new_actions, log_prob, _ = self.policy.sample(states_t)
        q1_new = self.critic1(states_t, new_actions)
        q2_new = self.critic2(states_t, new_actions)
        q_new = torch.min(q1_new, q2_new)
        actor_loss = (self.alpha * log_prob - q_new).mean()

        self.policy_optimizer.zero_grad()
        actor_loss.backward()
        self.policy_optimizer.step()

        for param, target_param in zip(self.critic1.parameters(), self.critic1_target.parameters()):
            target_param.data.copy_(self.tau * param.data + (1.0 - self.tau) * target_param.data)
        for param, target_param in zip(self.critic2.parameters(), self.critic2_target.parameters()):
            target_param.data.copy_(self.tau * param.data + (1.0 - self.tau) * target_param.data)

        return {
            "critic_loss": float((critic1_loss + critic2_loss).item() / 2.0),
            "actor_loss": float(actor_loss.item())
        }

    def save(self, filepath: Union[str, Path]):
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "policy": self.policy.state_dict(),
            "critic1": self.critic1.state_dict(),
            "critic2": self.critic2.state_dict(),
            "total_steps": self.total_steps
        }, p)
        logger.info(f"SAC Continuous Model saved to {p}")

    def load(self, filepath: Union[str, Path]) -> bool:
        p = Path(filepath)
        if not p.exists():
            return False
        try:
            checkpoint = torch.load(p, map_location=self.device, weights_only=False)
            self.policy.load_state_dict(checkpoint["policy"])
            self.critic1.load_state_dict(checkpoint["critic1"])
            self.critic2.load_state_dict(checkpoint["critic2"])
            self.total_steps = checkpoint.get("total_steps", 0)
            logger.info(f"SAC Continuous Model loaded from {p}")
            return True
        except Exception as e:
            logger.error(f"Error loading SAC model: {e}")
            return False
