"""
SEMS Cost Optimizer Module
Calculates electricity costs based on actual grid consumption and predictions
from the historical TNEB dataset. Compares actual costs against user spending budget.
Minimizes grid consumption and electricity costs without artificially reducing demand.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("SEMS.CostOptimizer")

class CostOptimizer:
    """
    Cost Optimization layer for SEMS.
    - Computes authentic electricity cost: Grid Energy (kWh) * Electricity Price (₹/kWh)
    - Validates against user budget (Within Budget vs Budget Exceeded)
    - Minimizes grid dependency and cost while strictly maintaining household load.
    """

    def __init__(self, default_budget: float = 25.0):
        self.default_budget = float(default_budget)

    def calculate_cost(
        self,
        grid_power_kw: float,
        dt_hours: float,
        electricity_price: float
    ) -> float:
        """
        Calculates the estimated electricity cost based on actual grid usage.
        Formula: Grid Energy (kWh) * Electricity Price (₹/kWh)
        where Grid Energy = grid_power_kw * dt_hours
        """
        grid_kw = max(0.0, float(grid_power_kw))
        dt = max(0.0, float(dt_hours))
        price = max(0.0, float(electricity_price))
        
        grid_energy_kwh = grid_kw * dt
        estimated_cost = round(grid_energy_kwh * price, 4)
        return estimated_cost

    def evaluate_budget(
        self,
        estimated_cost: float,
        user_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compares estimated cost vs user budget.
        Returns budget status and user-facing explanation.
        Never artificially reduces household load just to satisfy budget.
        """
        budget = float(user_budget if user_budget is not None else self.default_budget)
        cost = float(estimated_cost)

        if cost <= budget:
            status = "Within Budget"
            message = f"Energy cost (₹{cost:.2f}) is within the configured budget limit of ₹{budget:.2f}."
            is_exceeded = False
        else:
            status = "Budget Exceeded"
            message = "Budget limit cannot be achieved under current energy conditions."
            is_exceeded = True

        remaining_budget = max(0.0, round(budget - cost, 2))
        cost_overrun = max(0.0, round(cost - budget, 2))

        return {
            "estimated_cost": cost,
            "user_budget": budget,
            "budget_status": status,
            "budget_exceeded": is_exceeded,
            "remaining_budget": remaining_budget,
            "cost_overrun": cost_overrun,
            "message": message
        }

    def optimize_dispatch_economics(
        self,
        household_demand_kw: float,
        solar_power_kw: float,
        battery_power_kw: float,
        grid_power_kw: float,
        dt_hours: float,
        electricity_price: float,
        user_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyzes the economic efficiency and bill savings of the energy allocation.
        Compares baseline cost (100% grid supply) vs optimized hybrid allocation.
        """
        demand_kw = max(0.0, float(household_demand_kw))
        dt = max(0.0, float(dt_hours))
        price = max(0.0, float(electricity_price))
        budget = float(user_budget if user_budget is not None else self.default_budget)

        # Baseline cost if all demand were supplied by grid
        baseline_grid_energy = demand_kw * dt
        baseline_cost = round(baseline_grid_energy * price, 4)

        # Actual cost under optimized allocation
        actual_grid_energy = max(0.0, float(grid_power_kw)) * dt
        actual_cost = round(actual_grid_energy * price, 4)

        savings_inr = round(max(0.0, baseline_cost - actual_cost), 4)
        savings_pct = round((savings_inr / baseline_cost * 100.0), 1) if baseline_cost > 0.0 else 0.0

        budget_eval = self.evaluate_budget(actual_cost, user_budget=budget)

        return {
            "estimated_cost": actual_cost,
            "baseline_cost": baseline_cost,
            "savings_inr": savings_inr,
            "savings_pct": savings_pct,
            "user_budget": budget,
            "budget_status": budget_eval["budget_status"],
            "budget_exceeded": budget_eval["budget_exceeded"],
            "budget_message": budget_eval["message"],
            "grid_energy_kwh": round(actual_grid_energy, 4),
            "electricity_price_inr": price
        }
