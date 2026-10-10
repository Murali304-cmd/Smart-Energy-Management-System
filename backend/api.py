import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel, Field

from api.solar_api import get_realtime_solar_generation
from api.smart_meter_api import get_current_energy_usage
from api.battery_api import get_bess_telemetry, get_battery_telemetry, get_battery_provider
from energy.energy_flow import get_energy_flow_manager
from energy.energy_manager import get_energy_manager
from energy.energy_state import get_energy_state_manager
from services.alert_service import AlertService

logger = logging.getLogger("SEMS.BackendAPI")
energy_router = APIRouter()

# Global alert service reference (can be injected from server.py)
_alert_service: Optional[AlertService] = None

def set_alert_service(alert_service_instance: AlertService):
    global _alert_service
    _alert_service = alert_service_instance

def _get_alert_service() -> AlertService:
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service

class BackupConfigRequest(BaseModel):
    desired_backup_hours: float = Field(default=10.0, ge=1.0, le=48.0)
    average_household_load_kw: Optional[float] = Field(default=None, ge=0.2, le=20.0)

class DailyNotifyRequest(BaseModel):
    user_budget: Optional[float] = Field(default=25.0, ge=0.0, le=1000.0)

class EnergyManageRequest(BaseModel):
    predicted_solar: float = Field(..., ge=0.0, description="Predicted solar generation in kW")
    household_demand: float = Field(..., ge=0.0, description="Household demand in kW")
    predicted_price: float = Field(..., ge=0.0, description="Predicted electricity price in INR/kWh")
    battery_soc: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Battery SOC %")
    user_budget: Optional[float] = Field(default=25.0, ge=0.0, description="User spending budget in INR")
    dt_hours: Optional[float] = Field(default=0.25, ge=0.01, le=1.0, description="Time step duration in hours")
    grid_available: Optional[bool] = Field(default=True, description="Whether grid connection is available")

@energy_router.post("/energy/manage")
def manage_energy_allocation(req: EnergyManageRequest) -> Dict[str, Any]:
    """
    Central Energy Management endpoint:
    Processes ML predictions, battery parameters, and budget through
    Cost Optimization + Energy Allocation + Battery Management + Grid Management.
    """
    mgr = get_energy_manager()
    result = mgr.process_energy_decision(
        predicted_solar=req.predicted_solar,
        household_demand=req.household_demand,
        predicted_price=req.predicted_price,
        battery_soc=req.battery_soc,
        user_budget=req.user_budget,
        dt_hours=req.dt_hours or 0.25,
        grid_available=req.grid_available if req.grid_available is not None else True
    )
    return result

@energy_router.get("/energy/manage")
def get_energy_allocation_query(
    predicted_solar: Optional[float] = Query(default=None, ge=0.0, description="Predicted solar generation (kW)"),
    household_demand: Optional[float] = Query(default=None, ge=0.0, description="Household load (kW)"),
    predicted_price: Optional[float] = Query(default=None, ge=0.0, description="Predicted price (INR/kWh)"),
    battery_soc: Optional[float] = Query(default=None, ge=0.0, le=100.0, description="Battery SOC %"),
    user_budget: float = Query(default=25.0, ge=0.0, description="User budget (INR)")
) -> Dict[str, Any]:
    """GET query variant of central Energy Management decision."""
    if predicted_solar is None:
        solar_res = get_realtime_solar_generation()
        predicted_solar = float(solar_res.get("solar_power_kw", 2.5))
    if household_demand is None:
        meter_res = get_current_energy_usage()
        household_demand = float(meter_res.get("energy_usage", 1.8))
    if predicted_price is None:
        predicted_price = 4.70

    mgr = get_energy_manager()
    return mgr.process_energy_decision(
        predicted_solar=predicted_solar,
        household_demand=household_demand,
        predicted_price=predicted_price,
        battery_soc=battery_soc,
        user_budget=user_budget
    )

@energy_router.get("/energy-flow")
def get_realtime_energy_flow(
    solar_kw: Optional[float] = Query(default=None, description="Optional override for solar generation in kW"),
    load_kw: Optional[float] = Query(default=None, description="Optional override for household load in kW"),
    battery_soc: Optional[float] = Query(default=None, description="Optional override for battery SOC %"),
    user_budget: Optional[float] = Query(default=25.0, description="User budget limit in INR")
) -> Dict[str, Any]:
    """
    Returns authentic real-time Solar -> Household Load -> Battery -> Grid energy flow,
    battery charging/discharging state, and dynamic 10-hour backup metrics.
    """
    # 1. Obtain Real-Time Solar Generation
    if solar_kw is not None:
        actual_solar_kw = max(0.0, float(solar_kw))
    else:
        solar_res = get_realtime_solar_generation()
        actual_solar_kw = float(solar_res.get("solar_power_kw", 0.0))

    # 2. Obtain Real-Time Household Demand
    if load_kw is not None:
        actual_load_kw = max(0.1, float(load_kw))
    else:
        meter_res = get_current_energy_usage()
        actual_load_kw = float(meter_res.get("energy_usage", 1.8))

    # 3. Process Real-Time Energy Flow with physical priority & energy balance
    flow_mgr = get_energy_flow_manager()
    flow_result = flow_mgr.process_realtime_flow(
        solar_generation_kw=actual_solar_kw,
        household_demand_kw=actual_load_kw,
        current_soc=battery_soc,
        user_budget=float(user_budget or 25.0)
    )

    return flow_result

@energy_router.get("/battery")
def get_battery() -> Dict[str, Any]:
    """Returns normalized battery telemetry from configured provider (Enode / Sandbox / Demo)."""
    return get_battery_telemetry()

@energy_router.get("/battery/status")
def get_battery_status() -> Dict[str, Any]:
    """Returns detailed connection status, battery availability, API status, and mode."""
    provider = get_battery_provider()
    status_info = provider.check_connection()
    telemetry = provider.get_telemetry()
    return {
        "mode": status_info.get("mode", "demo"),
        "connected": status_info.get("connected", False),
        "connection_status": "connected" if status_info.get("connected") else "disconnected",
        "battery_availability": status_info.get("battery_available", False),
        "battery_available": status_info.get("battery_available", False),
        "api_status": status_info.get("api_status", "unknown"),
        "status": telemetry.get("status", "unavailable"),
        "last_update_time": status_info.get("last_update_time", datetime.now(timezone.utc).isoformat()),
        "battery_id": telemetry.get("battery_id"),
        "manufacturer": telemetry.get("manufacturer"),
        "model": telemetry.get("model"),
        "error": status_info.get("error") or telemetry.get("error")
    }

@energy_router.get("/battery/backup")
def get_battery_backup(
    load_kw: Optional[float] = Query(default=None, ge=0.0, description="Current load override (kW)"),
    desired_hours: Optional[float] = Query(default=10.0, ge=1.0, description="Desired backup target in hours")
) -> Dict[str, Any]:
    """Returns dynamic capacity, usable energy, expected load, estimated backup hours, and 10-hour backup availability."""
    telemetry = get_battery_telemetry()
    flow_mgr = get_energy_flow_manager()
    state = flow_mgr.state_manager.get_state()

    current_soc = telemetry.get("soc_percent")
    if current_soc is None:
        current_soc = float(state.get("battery_soc", 75.0))

    capacity_kwh = telemetry.get("capacity_kwh")
    if capacity_kwh is None:
        capacity_kwh = flow_mgr.capacity_kwh

    if load_kw is not None:
        effective_load = max(0.1, float(load_kw))
    else:
        effective_load = float(state.get("household_load_kw", 1.8))

    metrics = flow_mgr.backup_calculator.calculate_backup_metrics(
        current_soc=current_soc,
        current_load_kw=effective_load,
        desired_hours=desired_hours,
        battery_capacity_kwh=capacity_kwh
    )

    return {
        "mode": telemetry.get("mode", "demo"),
        "connected": telemetry.get("connected", False),
        "capacity_kwh": metrics["capacity_kwh"],
        "usable_energy_kwh": metrics["usable_energy_kwh"],
        "available_energy_kwh": metrics["available_battery_energy_kwh"],
        "expected_load_kw": metrics["expected_load_kw"],
        "estimated_backup_hours": metrics["estimated_backup_hours"],
        "required_backup_hours": metrics["required_backup_hours"],
        "ten_hour_backup_available": metrics["ten_hour_backup_available"],
        "backup_status": metrics["backup_status"],
        "status_label": metrics["status_label"],
        "current_soc": metrics["current_soc"],
        "timestamp": telemetry.get("timestamp", datetime.now(timezone.utc).isoformat())
    }

@energy_router.post("/energy/backup-config")
def update_backup_config(config: BackupConfigRequest) -> Dict[str, Any]:
    """Allows user/admin to configure desired backup hours and inspect required battery capacity."""
    flow_mgr = get_energy_flow_manager()
    flow_mgr.backup_calculator.desired_backup_hours = float(config.desired_backup_hours)
    if config.average_household_load_kw is not None:
        flow_mgr.backup_calculator.avg_load_kw = float(config.average_household_load_kw)

    state = flow_mgr.state_manager.get_state()
    current_soc = state.get("battery_soc", 75.0)
    current_load = state.get("household_load_kw", 1.8)

    metrics = flow_mgr.backup_calculator.calculate_backup_metrics(
        current_soc=current_soc,
        current_load_kw=current_load
    )
    return {
        "status": "success",
        "message": f"Backup target set to {config.desired_backup_hours} hours.",
        "metrics": metrics
    }

@energy_router.get("/summary/daily")
def get_daily_energy_summary(budget: float = Query(default=25.0)) -> Dict[str, Any]:
    """Calculates daily energy summary and budget compliance."""
    state = get_energy_state_manager().get_state()
    solar_kwh = float(state.get("today_solar_kwh", 6.8))
    battery_kwh = float(state.get("today_battery_discharge_kwh", 3.2))
    grid_kwh = float(state.get("today_grid_import_kwh", 2.6))
    grid_export_kwh = float(state.get("today_grid_export_kwh", 0.9))
    total_consumed_kwh = round(solar_kwh + battery_kwh + grid_kwh, 2)
    cost_inr = round(float(state.get("today_cost_inr", 15.60)), 2)
    budget_inr = float(budget)
    savings_inr = round(max(0.0, (total_consumed_kwh * 4.70) - cost_inr), 2)
    clean_pct = min(100.0, round(((solar_kwh + battery_kwh) / max(0.1, total_consumed_kwh)) * 100.0, 1))

    return {
        "status": "success",
        "date": state.get("current_date", datetime.now().strftime("%Y-%m-%d")),
        "solar_kwh": solar_kwh,
        "battery_kwh": battery_kwh,
        "grid_kwh": grid_kwh,
        "grid_export_kwh": grid_export_kwh,
        "total_consumed_kwh": total_consumed_kwh,
        "daily_cost_inr": cost_inr,
        "daily_budget_inr": budget_inr,
        "savings_inr": savings_inr,
        "clean_energy_percentage": clean_pct,
        "budget_status": "within_budget" if cost_inr <= budget_inr else "exceeded_budget"
    }

@energy_router.post("/summary/daily/notify")
def trigger_daily_summary_notification(req: DailyNotifyRequest = Body(default=DailyNotifyRequest())) -> Dict[str, Any]:
    """Generates daily summary alert and pushes to notification center."""
    summary = get_daily_energy_summary(budget=req.user_budget or 25.0)
    alerts = _get_alert_service()
    alert_record = alerts.record_daily_summary(
        solar_kwh=summary["solar_kwh"],
        battery_kwh=summary["battery_kwh"],
        grid_kwh=summary["grid_kwh"],
        total_kwh=summary["total_consumed_kwh"],
        cost_inr=summary["daily_cost_inr"],
        budget_inr=summary["daily_budget_inr"],
        savings_inr=summary["savings_inr"],
        clean_pct=summary["clean_energy_percentage"]
    )
    return {
        "status": "success",
        "message": "Daily summary notification dispatched successfully.",
        "alert": alert_record,
        "summary": summary
    }

@energy_router.post("/notifications/hourly-trigger")
def trigger_hourly_usage_notification() -> Dict[str, Any]:
    """Generates hourly usage alert specifying what sources were used."""
    state = get_energy_state_manager().get_state()
    solar_kw = float(state.get("solar_power_kw", 0.0))
    batt_kw = float(state.get("battery_power_kw", 0.0))
    batt_mode = state.get("battery_mode", "idle")
    grid_kw = float(state.get("grid_power_kw", 0.0))
    load_kw = float(state.get("household_load_kw", 1.8))
    cost_inr = round(grid_kw * 0.25 * 4.70, 2)

    alerts = _get_alert_service()
    alert_record = alerts.record_hourly_usage(
        solar_kwh=solar_kw,
        battery_kwh=batt_kw if batt_mode == "discharging" else 0.0,
        grid_kwh=grid_kw,
        total_kwh=load_kw,
        cost_inr=cost_inr
    )
    return {
        "status": "success",
        "message": "Hourly usage notification dispatched.",
        "alert": alert_record,
        "notification": {
            "title": f"⚡ 1-Hour Energy & Demand Report ({datetime.now().strftime('%I:%M %p')})",
            "body": f"Past 1 hr: {load_kw:.2f} kWh (₹ {cost_inr:.2f}) | Solar: {solar_kw:.2f} kWh | Grid: {grid_kw:.2f} kWh",
            "tag": "sems_hourly_report",
            "timestamp": datetime.now().isoformat()
        }
    }

class EventNotificationTracker:
    def __init__(self, cooldown_seconds: float = 300.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_state: Dict[str, Any] = {}
        self.last_event_timestamps: Dict[str, float] = {}
        self.events_history: List[Dict[str, Any]] = []

    def evaluate_and_generate_events(self, current_flow: Dict[str, Any]) -> List[Dict[str, Any]]:
        import time
        now_ts = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        new_events = []

        solar_kw = float(current_flow.get("solar_power_kw", 0.0))
        load_kw = float(current_flow.get("household_load_kw", 1.8))
        batt_mode = current_flow.get("battery_mode", "idle")
        batt_soc = float(current_flow.get("battery_soc", 75.0))
        grid_kw = float(current_flow.get("grid_power_kw", 0.0))
        est_backup = float(current_flow.get("estimated_backup_hours", 4.8))
        req_backup = float(current_flow.get("required_backup_hours", 10.0))
        max_soc = float(current_flow.get("battery_max_soc", 100.0))

        prev = self.last_state

        def can_fire(event_key: str) -> bool:
            last_t = self.last_event_timestamps.get(event_key, 0.0)
            return (now_ts - last_t) >= self.cooldown_seconds

        def record_event(evt_id: str, evt_type: str, title: str, message: str, severity: str, action_target: str):
            evt = {
                "id": f"{evt_type}_{int(now_ts * 1000)}",
                "type": evt_type,
                "title": title,
                "message": message,
                "severity": severity,
                "action_target": action_target,
                "timestamp": now_iso
            }
            new_events.append(evt)
            self.events_history.insert(0, evt)
            if len(self.events_history) > 50:
                self.events_history.pop()
            self.last_event_timestamps[evt_type] = now_ts

        # A. High Solar Generation (solar_power > household_load)
        if solar_kw > load_kw:
            if (prev.get("solar_power_kw", 0.0) <= prev.get("household_load_kw", 0.0) or can_fire("solar_available")):
                record_event(
                    "solar_avail", "solar_available",
                    "☀️ Solar Energy Available",
                    "Solar generation is higher than current household demand. Excess solar is being used to charge the battery.",
                    "info", "solar"
                )

        # B. Battery Charging
        if batt_mode == "charging":
            if (prev.get("battery_mode") != "charging" or can_fire("battery_charging")):
                record_event(
                    "batt_charge", "battery_charging",
                    "🔋 Battery Charging",
                    f"Excess solar energy is charging the battery. Current battery SOC: {batt_soc:.0f}%.",
                    "info", "battery"
                )

        # C. Battery Full
        if batt_soc >= (max_soc - 0.5):
            if (prev.get("battery_soc", 0.0) < (max_soc - 0.5) or can_fire("battery_full")):
                record_event(
                    "batt_full", "battery_full",
                    "🔋 Battery Fully Charged",
                    "The battery has reached its maximum SOC. Additional excess solar can be exported to the grid.",
                    "info", "battery"
                )

        # D. Low Battery (<= 25%)
        if batt_soc <= 25.0:
            if (prev.get("battery_soc", 100.0) > 25.0 or can_fire("battery_low")):
                record_event(
                    "batt_low", "battery_low",
                    "⚠️ Low Battery",
                    "Battery SOC is low. SEMS may use the grid if solar and battery power cannot satisfy the household demand.",
                    "warning", "battery"
                )

        # E. Grid Power Activated
        if grid_kw > 0.05:
            if (prev.get("grid_power_kw", 0.0) <= 0.05 or can_fire("grid_activated")):
                record_event(
                    "grid_act", "grid_activated",
                    "⚡ Grid Power Activated",
                    "Solar and battery power are insufficient to meet the current household demand. Grid power is now being used.",
                    "important", "grid"
                )

        # F. Grid Usage Stopped
        if grid_kw <= 0.05 and prev.get("grid_power_kw", 0.0) > 0.05:
            if can_fire("grid_stopped"):
                record_event(
                    "grid_stop", "grid_stopped",
                    "✅ Grid Usage Stopped",
                    "Household demand is currently being satisfied without grid power.",
                    "info", "grid"
                )

        # G. 10-Hour Backup Status
        if est_backup >= req_backup:
            if (prev.get("estimated_backup_hours", 0.0) < req_backup or can_fire("backup_satisfied")):
                record_event(
                    "bk_sat", "backup_satisfied",
                    "🔋 Backup Requirement Satisfied",
                    f"The battery currently has enough available energy for approximately {est_backup:.1f} hours of backup.",
                    "info", "backup"
                )
        else:
            if (prev.get("estimated_backup_hours", req_backup) >= req_backup or can_fire("backup_not_met")):
                record_event(
                    "bk_short", "backup_not_met",
                    "⚠️ Backup Requirement Not Met",
                    f"Current battery energy provides approximately {est_backup:.1f} hours of backup. Required backup duration is 10 hours.",
                    "warning", "backup"
                )

        self.last_state = {
            "solar_power_kw": solar_kw,
            "household_load_kw": load_kw,
            "battery_mode": batt_mode,
            "battery_soc": batt_soc,
            "grid_power_kw": grid_kw,
            "estimated_backup_hours": est_backup,
            "required_backup_hours": req_backup
        }
        return new_events

_notification_tracker = EventNotificationTracker(cooldown_seconds=300.0)

@energy_router.get("/notifications")
def get_system_notifications(limit: int = Query(default=20, ge=1, le=50)) -> Dict[str, Any]:
    """
    Returns authentic SEMS event notifications generated from actual real-time
    solar generation, household load, battery SOC, grid usage, and backup duration.
    """
    # 1. Fetch current flow snapshot
    flow_mgr = get_energy_flow_manager()
    state = flow_mgr.state_manager.get_state()
    current_flow = flow_mgr.process_realtime_flow(
        solar_generation_kw=float(state.get("solar_power_kw", 0.0)),
        household_demand_kw=float(state.get("household_load_kw", 1.8)),
        current_soc=float(state.get("battery_soc", 75.0))
    )

    # 2. Run state-transition & event evaluation
    new_events = _notification_tracker.evaluate_and_generate_events(current_flow)

    return {
        "status": "success",
        "new_events": new_events,
        "notifications": _notification_tracker.events_history[:limit],
        "total": len(_notification_tracker.events_history),
        "cooldown_seconds": _notification_tracker.cooldown_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


