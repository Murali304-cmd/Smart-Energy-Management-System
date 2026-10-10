import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api import EventNotificationTracker
from server import app

client = TestClient(app)

def test_event_notification_tracker_transitions():
    tracker = EventNotificationTracker(cooldown_seconds=300.0)

    # State 1: Solar surplus charging battery
    flow_1 = {
        "solar_power_kw": 5.0,
        "household_load_kw": 2.0,
        "battery_mode": "charging",
        "battery_soc": 80.0,
        "grid_power_kw": 0.0,
        "estimated_backup_hours": 6.0,
        "required_backup_hours": 10.0,
        "battery_max_soc": 100.0
    }
    events_1 = tracker.evaluate_and_generate_events(flow_1)
    # Should detect solar available, battery charging, and backup not met
    event_types_1 = [e["type"] for e in events_1]
    assert "solar_available" in event_types_1
    assert "battery_charging" in event_types_1

    # State 2: Identical state immediately after -> NO DUPLICATE EVENTS (anti-spam)
    events_2 = tracker.evaluate_and_generate_events(flow_1)
    assert len(events_2) == 0, "Duplicate notifications should NOT be generated on unchanged state"

    # State 3: Solar drops, Grid activates (transition 0 -> 2.5 kW)
    flow_3 = {
        "solar_power_kw": 0.0,
        "household_load_kw": 4.0,
        "battery_mode": "idle",
        "battery_soc": 20.0,
        "grid_power_kw": 4.0,
        "estimated_backup_hours": 0.5,
        "required_backup_hours": 10.0,
        "battery_max_soc": 100.0
    }
    events_3 = tracker.evaluate_and_generate_events(flow_3)
    event_types_3 = [e["type"] for e in events_3]
    assert "grid_activated" in event_types_3
    assert "battery_low" in event_types_3

    # State 4: Grid stops
    flow_4 = {
        "solar_power_kw": 4.0,
        "household_load_kw": 3.0,
        "battery_mode": "charging",
        "battery_soc": 40.0,
        "grid_power_kw": 0.0,
        "estimated_backup_hours": 3.0,
        "required_backup_hours": 10.0,
        "battery_max_soc": 100.0
    }
    events_4 = tracker.evaluate_and_generate_events(flow_4)
    event_types_4 = [e["type"] for e in events_4]
    assert "grid_stopped" in event_types_4

def test_api_notifications_endpoint():
    response = client.get("/api/notifications?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "notifications" in data
    assert "cooldown_seconds" in data
    assert data["cooldown_seconds"] == 300.0
    assert isinstance(data["notifications"], list)
