import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import (
    DQN_EPISODES,
    DQN_LEARNING_RATE,
    DQN_GAMMA,
    DQN_EPSILON_START,
    DQN_EPSILON_MIN,
    DQN_EPSILON_DECAY,
    DQN_BATCH_SIZE,
    DQN_MEMORY_SIZE,
    DQN_TARGET_UPDATE_FREQ,
    DQN_MODEL_PATH,
    DQN_META_PATH,
    PROCESSED_DATA_DIR
)
from recommendation.environment import (
    EnergyManagementEnv,
    ACTION_NAMES,
    STATE_DIM,
    ACTION_DIM,
    ACTION_SOLAR_PRIORITY,
    ACTION_BATTERY_DISPATCH,
    ACTION_GRID_USAGE,
    ACTION_PEAK_SHAVING
)
from recommendation.dqn_model import DQNAgent, StateScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SEMS.TrainDQN")
ARTIFACT_DIR = Path(r"C:\Users\mural\.gemini\antigravity-ide\brain\ef5499b0-9c54-4e91-9d83-434200f03153")

def generate_comprehensive_training_scenarios() -> List[List[np.ndarray]]:
    """
    Builds diverse real-world scenario sequences experiencing:
    - High solar / Low solar / Night zero solar
    - High load / Low load / Peak load
    - Peak tariff (₹7.50) / Off-peak tariff (₹4.70)
    - High SoC (80-95%) / Low SoC (20-25%) / Medium SoC (50-60%)
    """
    weather_path = PROCESSED_DATA_DIR / "weather_processed.csv"
    energy_path = PROCESSED_DATA_DIR / "energy_processed.csv"
    
    scenarios = []
    
    # 1. Real historical multi-day trajectories
    if weather_path.exists() and energy_path.exists():
        try:
            df_w = pd.read_csv(weather_path)
            df_e = pd.read_csv(energy_path)
            min_len = min(len(df_w), len(df_e))
            if min_len >= 48:
                if "solar_generation_kw" in df_w.columns:
                    solar_gen = df_w["solar_generation_kw"].values[:min_len]
                else:
                    solar_gen = (df_w["solar_irradiance"].values[:min_len] / 1000.0) * 5.0 * 0.82
                    
                load_vals = df_e["energy_usage"].values[:min_len]
                hours = df_e["hour"].values[:min_len] if "hour" in df_e.columns else (np.arange(min_len) * 0.5) % 24
                
                # Split into 24-step (12h) and 48-step (24h) episodes
                chunk_len = 24
                for start in range(0, min_len - chunk_len, chunk_len):
                    chunk = []
                    initial_soc = float(np.random.choice([25.0, 45.0, 70.0, 90.0]))
                    for i in range(start, start + chunk_len):
                        h = hours[i]
                        s_p = float(max(0.0, solar_gen[i]))
                        l_p = float(max(0.2, load_vals[i]))
                        is_peak = 1.0 if (18 <= h <= 22) else 0.0
                        price = 7.50 if is_peak else 4.70
                        curr_l = l_p
                        # State: [solar_pred, load_pred, electricity_price, battery_soc, current_load, time_peak_indicator]
                        chunk.append(np.array([s_p, l_p, price, initial_soc, curr_l, is_peak], dtype=np.float32))
                    scenarios.append(chunk)
        except Exception as e:
            logger.warning(f"Error loading historical CSVs for DQN scenarios: {e}")

    # 2. Targeted stress-testing scenarios across the 8 key operational permutations
    permutations = [
        {"name": "High Solar, Low Load, Off-Peak, Low SoC", "solar": (3.0, 4.5), "load": (0.8, 1.5), "peak": 0.0, "price": 4.70, "soc": 25.0},
        {"name": "High Solar, High Load, Off-Peak, High SoC", "solar": (3.5, 4.5), "load": (3.0, 4.2), "peak": 0.0, "price": 4.70, "soc": 85.0},
        {"name": "Zero Solar (Night), Peak Load, Peak Tariff, High SoC", "solar": (0.0, 0.0), "load": (3.5, 5.0), "peak": 1.0, "price": 7.50, "soc": 80.0},
        {"name": "Zero Solar (Night), Peak Load, Peak Tariff, Depleted SoC", "solar": (0.0, 0.0), "load": (3.0, 4.5), "peak": 1.0, "price": 7.50, "soc": 20.0},
        {"name": "Zero Solar (Night), Low Load, Off-Peak Tariff, Low SoC", "solar": (0.0, 0.0), "load": (0.6, 1.2), "peak": 0.0, "price": 4.70, "soc": 30.0},
        {"name": "Mid Solar, Mid Load, Standard Tariff, Mid SoC", "solar": (1.5, 2.5), "load": (1.5, 2.5), "peak": 0.0, "price": 4.70, "soc": 55.0},
        {"name": "Surplus Solar, Low Load, Battery 100% Full", "solar": (4.0, 4.5), "load": (1.0, 1.5), "peak": 0.0, "price": 4.70, "soc": 98.0},
        {"name": "Cloudy Day Low Solar, High Load, Standard Tariff, Medium SoC", "solar": (0.2, 0.8), "load": (2.5, 3.8), "peak": 0.0, "price": 4.70, "soc": 50.0}
    ]

    for p in permutations:
        for _ in range(5):
            seq = []
            soc = p["soc"]
            for step in range(24):
                s = float(np.random.uniform(p["solar"][0], p["solar"][1]))
                l = float(np.random.uniform(p["load"][0], p["load"][1]))
                price = p["price"]
                is_p = p["peak"]
                seq.append(np.array([s, l, price, soc, l, is_p], dtype=np.float32))
            scenarios.append(seq)
            
    logger.info(f"Generated {len(scenarios)} diverse training scenario trajectories.")
    return scenarios

def train_dqn(
    episodes: int = 150,
    save_path: Path = DQN_MODEL_PATH,
    meta_path: Path = DQN_META_PATH
) -> Dict[str, Any]:
    logger.info(f"Starting DQN Training for {episodes} episodes with redesigned 6D state & 4 physical actions...")
    env = EnergyManagementEnv()
    scaler = StateScaler()
    agent = DQNAgent(
        state_dim=STATE_DIM,
        action_dim=ACTION_DIM,
        learning_rate=0.001,
        gamma=0.95,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.985,
        batch_size=64,
        memory_size=15000,
        target_update_freq=10,
        scaler=scaler
    )

    scenarios = generate_comprehensive_training_scenarios()
    episode_rewards = []
    episode_losses = []
    action_counts = {k: 0 for k in ACTION_NAMES.keys()}

    for ep in range(1, episodes + 1):
        scenario_idx = (ep - 1) % len(scenarios)
        scenario_states = [s.copy() for s in scenarios[scenario_idx]]
        
        # Vary starting battery SoC realistically across episodes
        start_soc = float(np.random.uniform(20.0, 95.0))
        scenario_states[0][3] = start_soc
        
        state = env.reset(scenario_states[0])
        total_ep_reward = 0.0
        losses = []

        for step in range(len(scenario_states) - 1):
            action, _ = agent.select_action(state, eval_mode=False)
            action_counts[action] = action_counts.get(action, 0) + 1

            next_scenario_state = scenario_states[step + 1]
            next_state, reward, done, info = env.step(action, next_predicted_state=next_scenario_state)

            agent.memory.push(state, action, reward, next_state, done)
            loss = agent.train_step()
            if loss is not None:
                losses.append(loss)

            state = next_state
            total_ep_reward += reward

        episode_rewards.append(round(total_ep_reward, 2))
        avg_loss = float(np.mean(losses)) if losses else 0.0
        episode_losses.append(round(avg_loss, 4))

        if ep % 25 == 0 or ep == episodes:
            avg_recent = float(np.mean(episode_rewards[-25:]))
            logger.info(
                f"Episode {ep:03d}/{episodes} | Avg Reward (last 25): {avg_recent:.2f} | "
                f"Epsilon: {agent.epsilon:.4f} | Loss: {avg_loss:.4f}"
            )

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(save_path)

    # Plot Reward Convergence
    plt.figure(figsize=(9, 4.5))
    plt.plot(episode_rewards, color="#059669", lw=1.5, label="Episode Reward")
    # Rolling 15-episode average
    rolling_avg = pd.Series(episode_rewards).rolling(15, min_periods=1).mean()
    plt.plot(rolling_avg, color="#047857", lw=2.5, label="15-Episode Moving Average")
    plt.title("DQN Agent: Reward Convergence Curve")
    plt.xlabel("Training Episode")
    plt.ylabel("Cumulative Reward")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    reward_plot_path = ARTIFACT_DIR / "dqn_reward_convergence.png"
    plt.savefig(reward_plot_path, dpi=200)
    plt.close()

    total_actions = sum(action_counts.values())
    action_dist_pct = {
        ACTION_NAMES.get(k, str(k)): round((v / max(1, total_actions)) * 100.0, 1)
        for k, v in action_counts.items()
    }

    metadata = {
        "status": "trained",
        "model_type": "Deep Q-Network (DQN) - Intelligent SEMS Energy Dispatch Recommender",
        "training_timestamp": pd.Timestamp.now().isoformat(),
        "state_dim": STATE_DIM,
        "action_dim": ACTION_DIM,
        "state_features": [
            "predicted_solar (kW)",
            "predicted_load (kW)",
            "electricity_price (₹/kWh)",
            "battery_soc (%)",
            "current_load (kW)",
            "time_peak_indicator (0 or 1)"
        ],
        "action_space": ACTION_NAMES,
        "episodes_trained": episodes,
        "final_epsilon": round(agent.epsilon, 4),
        "mean_reward_last_50": round(float(np.mean(episode_rewards[-50:])), 2),
        "action_distribution_counts": {ACTION_NAMES.get(k, str(k)): v for k, v in action_counts.items()},
        "action_distribution_percent": action_dist_pct,
        "battery_constraints_enforced": {
            "min_soc": 20.0,
            "max_soc": 100.0,
            "max_charge_kw": 6.0,
            "max_discharge_kw": 10.0,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95
        },
        "model_path": str(save_path)
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"DQN Training Complete! Action distribution: {action_dist_pct}")
    logger.info(f"Model saved to {save_path}, metadata to {meta_path}")
    return metadata

if __name__ == "__main__":
    train_dqn()
