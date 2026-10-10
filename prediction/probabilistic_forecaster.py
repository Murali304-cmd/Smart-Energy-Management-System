import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger("SEMS.ProbabilisticForecaster")

class ProbabilisticForecaster:
    """
    Multi-Horizon Probabilistic Forecaster providing P10 (optimistic/lower bound),
    P50 (median estimate), and P90 (upper bound/worst-case load) with conformal error intervals.
    """

    def __init__(self, alpha: float = 0.10):
        # 90% confidence interval (alpha = 0.10)
        self.alpha = alpha
        self.historical_residuals: Dict[str, List[float]] = {
            "solar": [],
            "load": [],
            "price": []
        }

    def update_residuals(self, target_type: str, actual: float, predicted: float):
        if target_type in self.historical_residuals:
            res = abs(actual - predicted)
            self.historical_residuals[target_type].append(res)
            if len(self.historical_residuals[target_type]) > 500:
                self.historical_residuals[target_type].pop(0)

    def forecast_with_bounds(
        self,
        target_type: str,
        predicted_mean: float,
        horizon_steps: int = 24
    ) -> Dict[str, Any]:
        """Calculates P10, P50, and P90 forecast intervals using conformal quantile estimation."""
        residuals = self.historical_residuals.get(target_type, [])
        if len(residuals) >= 20:
            q_val = float(np.quantile(residuals, 1.0 - self.alpha))
        else:
            # Default heuristic margin based on typical domain variance
            default_margins = {"solar": 0.35, "load": 0.45, "price": 0.60}
            q_val = default_margins.get(target_type, 0.4)

        p50 = max(0.0, round(float(predicted_mean), 2))
        p10 = max(0.0, round(float(predicted_mean - q_val), 2))
        p90 = max(0.0, round(float(predicted_mean + q_val), 2))

        # Multi-horizon trajectory extrapolation
        horizon_traj = []
        for step in range(horizon_steps):
            decay = 1.0 + 0.015 * step  # Uncertainty grows with horizon
            step_margin = q_val * decay
            horizon_traj.append({
                "step_hour": step + 1,
                "p10": max(0.0, round(predicted_mean - step_margin, 2)),
                "p50": max(0.0, round(predicted_mean, 2)),
                "p90": max(0.0, round(predicted_mean + step_margin, 2))
            })

        return {
            "target": target_type,
            "mean_prediction": p50,
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "uncertainty_margin": round(q_val, 2),
            "confidence_level": f"{int((1 - self.alpha) * 100)}%",
            "horizon_forecast": horizon_traj
        }


class PhysicsInformedSolarLoss(nn.Module):
    """
    Physics-Informed Neural Network (PINN) Loss function for Photovoltaic Generation.
    Embeds temperature coefficient physics: P = G * A * eta * [1 + gamma*(T_cell - 25)]
    """
    def __init__(
        self,
        panel_area_m2: float = 18.0,
        nominal_efficiency: float = 0.20,
        temp_coefficient: float = -0.004,  # -0.4% per °C above 25°C
        physics_weight: float = 0.25
    ):
        super(PhysicsInformedSolarLoss, self).__init__()
        self.panel_area = panel_area_m2
        self.efficiency = nominal_efficiency
        self.gamma = temp_coefficient
        self.physics_weight = physics_weight
        self.mse = nn.MSELoss()

    def forward(
        self,
        predicted_solar: torch.Tensor,
        true_solar: torch.Tensor,
        irradiance: torch.Tensor,
        cell_temp: torch.Tensor
    ) -> torch.Tensor:
        # Data-driven MSE Loss
        data_loss = self.mse(predicted_solar, true_solar)

        # Physics-calculated theoretical power (kW)
        # G (W/m2) * Area (m2) * eta * [1 + gamma * (T - 25)] / 1000
        temp_derating = 1.0 + self.gamma * (cell_temp - 25.0)
        p_physics = (irradiance * self.panel_area * self.efficiency * temp_derating) / 1000.0
        p_physics = torch.clamp(p_physics, min=0.0)

        # Physical boundary penalty: penalize non-zero generation when irradiance == 0
        night_penalty = torch.mean(torch.relu(predicted_solar) * (irradiance < 5.0).float())

        # Discrepancy with physical model
        physics_loss = self.mse(predicted_solar, p_physics) + 2.0 * night_penalty

        return data_loss + self.physics_weight * physics_loss
