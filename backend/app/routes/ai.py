"""
Intelligent Decision Engine (DRL) Routes for SEMS.
Endpoints for State, Action, Reward, and Truthful Explanation.
Supports primary DQN and optional PPO agent.
"""
from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.energy import EnergyReading
from backend.app.models.house import House
from backend.app.models.rl_action import RLAction
from backend.app.models.user import User
from backend.app.dependencies import get_current_user, verify_house_access
from backend.app.preprocessing.pipeline import preprocessor
from backend.app.rl.dqn_agent import dqn_agent
from backend.app.rl.ppo_agent import ppo_agent
from backend.app.rl.reward import compute_step_reward
from backend.app.xai.rl_explanation import drl_explainer
from backend.app.services.energy_flow_service import ACTION_NAMES, energy_flow_engine
from backend.app.services.battery_service import battery_service

router = APIRouter(prefix="/ai", tags=["Intelligent Decision Engine"])

@router.get("/state/{house_id}")
def get_ai_state(
    house_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve normalized 12-dimensional state vector."""
    verify_house_access(house_id, current_user)
    house = db.query(House).filter(House.id == house_id).first()
    e_latest = db.query(EnergyReading).filter(EnergyReading.house_id == house_id).order_by(EnergyReading.timestamp.desc()).first()

    solar = e_latest.solar_power if e_latest else 3.2
    load = e_latest.load_power if e_latest else 2.1
    soc = e_latest.battery_soc if e_latest else battery_service.current_soc
    budget = house.monthly_budget if house else 3000.0
    import_tariff = house.import_tariff if house else 6.50

    now = datetime.now(timezone.utc)
    hour = now.hour + (now.minute / 60.0)

    grid_dep = max(0.0, (load - solar) / max(0.1, load))
    state_vec = preprocessor.prepare_drl_state(
        solar=solar,
        pred_solar=solar * 1.05,
        load=load,
        pred_load=load * 0.98,
        price=import_tariff,
        pred_price=import_tariff,
        battery_soc=soc,
        monthly_budget=budget,
        grid_status=1.0,
        grid_dep=grid_dep,
        hour=hour
    )

    return {
        "house_id": house_id,
        "timestamp": now,
        "state_dimension": len(state_vec),
        "normalized_state": [round(float(v), 4) for v in state_vec],
        "state_labels": [
            "solar_norm", "pred_solar_norm", "load_norm", "pred_load_norm",
            "price_norm", "pred_price_norm", "soc_norm", "budget_norm",
            "grid_status", "grid_dependency", "hour_cycle", "constraint_flag"
        ]
    }

@router.get("/action/{house_id}")
def get_ai_action(
    house_id: str,
    agent_type: str = Query(default="DQN", pattern="^(DQN|PPO)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute DRL action selection and save RLAction record.
    """
    verify_house_access(house_id, current_user)
    state_info = get_ai_state(house_id, current_user, db)
    state_vec = state_info["normalized_state"]

    if agent_type == "PPO":
        action_res = ppo_agent.select_action(state_vec, evaluate=True)
        action_idx = action_res["action"]
        q_or_probs = action_res["action_probabilities"]
    else:
        action_res = dqn_agent.select_action(state_vec, evaluate=True)
        action_idx = action_res["action"]
        q_or_probs = action_res["q_values"]

    # Compute physical action validation
    e_latest = db.query(EnergyReading).filter(EnergyReading.house_id == house_id).order_by(EnergyReading.timestamp.desc()).first()
    house = db.query(House).filter(House.id == house_id).first()

    solar = e_latest.solar_power if e_latest else 3.2
    load = e_latest.load_power if e_latest else 2.1
    price = house.import_tariff if house else 6.5
    export_price = house.export_tariff if house else 3.5

    flow_res = energy_flow_engine.compute_energy_flow(
        solar_kw=solar,
        load_kw=load,
        action=action_idx,
        battery=battery_service,
        import_tariff=price,
        export_tariff=export_price,
        dt_hours=0.25
    )

    step_cost = flow_res["financial_step"]["import_cost"]
    step_rev = flow_res["financial_step"]["export_revenue"]
    baseline_cost = (load * 0.25) * price

    rew_info = compute_step_reward(
        baseline_cost=baseline_cost,
        actual_cost=step_cost,
        export_revenue=step_rev,
        solar_utilized=solar > 0,
        soc=battery_service.current_soc,
        min_soc=battery_service.min_soc,
        max_soc=battery_service.max_soc,
        action=action_idx
    )

    # Persist in DB
    action_rec = RLAction(
        house_id=house_id,
        timestamp=datetime.now(timezone.utc),
        agent=agent_type,
        state=json.dumps(state_vec),
        action=action_idx,
        reward=rew_info["total_reward"]
    )
    db.add(action_rec)
    db.commit()
    db.refresh(action_rec)

    # Explanation derived from actual state
    explanation = drl_explainer.explain_action(
        action=action_idx,
        solar_kw=solar,
        load_kw=load,
        price_rate=price,
        battery_soc=battery_service.current_soc,
        min_soc=battery_service.min_soc,
        max_soc=battery_service.max_soc
    )

    return {
        "id": action_rec.id,
        "house_id": house_id,
        "timestamp": action_rec.timestamp,
        "agent": agent_type,
        "action": action_idx,
        "action_name": ACTION_NAMES[action_idx],
        "reward": rew_info["total_reward"],
        "reward_breakdown": rew_info,
        "action_distribution_or_q": q_or_probs,
        "energy_flow": flow_res,
        "explanation": explanation
    }

@router.get("/reward/{house_id}")
def get_ai_reward(
    house_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the latest reward and proposed design objective status."""
    verify_house_access(house_id, current_user)
    latest_action = db.query(RLAction).filter(RLAction.house_id == house_id).order_by(RLAction.timestamp.desc()).first()
    
    return {
        "house_id": house_id,
        "objective_notice": "Proposed design objective until experimentally validated.",
        "reward_formula": "Reward = Cost Saving + Solar Utilization + Export Revenue + Budget Compliance - Grid Cost - Battery Degradation - Constraint Violations",
        "latest_reward": latest_action.reward if latest_action else 0.0,
        "agent": latest_action.agent if latest_action else "DQN"
    }

@router.get("/explanation/{house_id}")
def get_ai_explanation(
    house_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve explainable AI breakdown for the active action decision."""
    verify_house_access(house_id, current_user)
    latest_action = db.query(RLAction).filter(RLAction.house_id == house_id).order_by(RLAction.timestamp.desc()).first()
    e_latest = db.query(EnergyReading).filter(EnergyReading.house_id == house_id).order_by(EnergyReading.timestamp.desc()).first()
    house = db.query(House).filter(House.id == house_id).first()

    action = latest_action.action if latest_action else 0
    solar = e_latest.solar_power if e_latest else 3.0
    load = e_latest.load_power if e_latest else 2.0
    price = house.import_tariff if house else 6.5

    return drl_explainer.explain_action(
        action=action,
        solar_kw=solar,
        load_kw=load,
        price_rate=price,
        battery_soc=battery_service.current_soc,
        min_soc=battery_service.min_soc,
        max_soc=battery_service.max_soc
    )
