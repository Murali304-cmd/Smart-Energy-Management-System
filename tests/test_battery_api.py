"""
Unit and Integration Tests for Real Battery API (Enode & Multi-Provider Architecture)
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.battery_api import (
    EnodeOAuth2Client,
    EnodeBatteryProvider,
    DemoBatteryProvider,
    BatteryClientFactory,
    get_battery_telemetry,
    get_bess_telemetry
)
from server import app

client = TestClient(app)


def test_enode_oauth2_missing_credentials():
    """OAuth2 client should raise ValueError when credentials are not configured."""
    auth = EnodeOAuth2Client(api_url="", client_id="", client_secret="")
    assert not auth.is_configured()
    with pytest.raises(ValueError, match="Enode credentials not configured"):
        auth.get_access_token()


def test_enode_oauth2_token_success():
    """OAuth2 client acquires and caches access token."""
    auth = EnodeOAuth2Client(
        api_url="https://enode-api.test.io",
        client_id="test_id",
        client_secret="test_secret"
    )
    assert auth.is_configured()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "mock_bearer_token_xyz",
        "expires_in": 3600
    }

    with patch("requests.post", return_value=mock_resp) as mock_post:
        token = auth.get_access_token()
        assert token == "mock_bearer_token_xyz"
        mock_post.assert_called_once()

        # Second call should use cached token without calling network
        token2 = auth.get_access_token()
        assert token2 == "mock_bearer_token_xyz"
        assert mock_post.call_count == 1


def test_demo_battery_provider_normalization():
    """Demo provider should return complete normalized telemetry marked with mode 'demo'."""
    provider = DemoBatteryProvider(capacity_kwh=20.0, min_soc=20.0, max_soc=100.0)
    assert provider.mode == "demo"
    telemetry = provider.get_telemetry()

    assert telemetry["mode"] == "demo"
    assert telemetry["connected"] is True
    assert "soc_percent" in telemetry
    assert telemetry["capacity_kwh"] in (20.0, 1000.0)
    assert telemetry["status"] in ("charging", "discharging", "idle")
    assert telemetry["min_soc_percent"] == 20.0
    assert telemetry["max_soc_percent"] == 100.0
    assert telemetry["error"] is None


def test_enode_provider_normalization_success():
    """Enode provider should normalize raw Enode battery telemetry into standard schema."""
    provider = EnodeBatteryProvider(
        api_url="https://enode-api.test.io",
        client_id="test_id",
        client_secret="test_secret",
        battery_id="batt_001",
        is_sandbox=False
    )

    # Mock token
    provider.auth_client._access_token = "valid_token"
    provider.auth_client._expires_at = 9999999999

    mock_enode_data = {
        "id": "batt_001",
        "batteryModel": {"brand": "Tesla", "model": "Powerwall 2"},
        "isReachable": True,
        "capacity": 13.5,
        "chargeState": {
            "batteryLevel": 72.5,
            "powerKw": -2.1,
            "isCharging": False
        },
        "minSoc": 15.0,
        "maxSoc": 100.0,
        "lastSeen": "2026-09-12T06:00:00Z"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_enode_data

    with patch("requests.get", return_value=mock_resp):
        telemetry = provider.get_telemetry()
        assert telemetry["mode"] == "real"
        assert telemetry["connected"] is True
        assert telemetry["battery_id"] == "batt_001"
        assert telemetry["manufacturer"] == "Tesla"
        assert telemetry["model"] == "Powerwall 2"
        assert telemetry["soc_percent"] == 72.5
        assert telemetry["capacity_kwh"] == 13.5
        assert telemetry["battery_power_kw"] == -2.1
        assert telemetry["discharge_power_kw"] == 2.1
        assert telemetry["status"] == "discharging"
        assert telemetry["available_energy_kwh"] > 0
        assert telemetry["error"] is None


def test_enode_provider_failure_returns_unavailable_no_fake_soc():
    """In REAL mode, if Enode API fails, it MUST return unavailable without inventing fake SOC."""
    provider = EnodeBatteryProvider(
        api_url="https://enode-api.test.io",
        client_id="test_id",
        client_secret="test_secret",
        battery_id="batt_001",
        is_sandbox=False
    )
    provider.auth_client._access_token = "valid_token"
    provider.auth_client._expires_at = 9999999999

    with patch("requests.get", side_effect=Exception("Connection refused")):
        telemetry = provider.get_telemetry()
        assert telemetry["mode"] == "real"
        assert telemetry["connected"] is False
        assert telemetry["soc_percent"] is None  # NO FAKE SOC
        assert telemetry["capacity_kwh"] is None
        assert telemetry["status"] == "unavailable"
        assert "Battery API" in telemetry["error"]


def test_battery_client_factory_modes():
    """Factory correctly instantiates providers based on mode."""
    p_real = BatteryClientFactory.get_provider("real")
    assert p_real.mode == "real"

    p_sandbox = BatteryClientFactory.get_provider("sandbox")
    assert p_sandbox.mode == "sandbox"

    p_demo = BatteryClientFactory.get_provider("demo")
    assert p_demo.mode == "demo"


def test_fastapi_get_battery_endpoint():
    """GET /api/battery returns standard normalized response."""
    resp = client.get("/api/battery")
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "connected" in data
    assert "status" in data
    assert "soc_percent" in data or data.get("status") == "unavailable"


def test_fastapi_get_battery_status_endpoint():
    """GET /api/battery/status returns connection and health info."""
    resp = client.get("/api/battery/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "connected" in data
    assert "battery_availability" in data
    assert "connection_status" in data


def test_fastapi_get_battery_backup_endpoint():
    """GET /api/battery/backup calculates dynamic 10-hour backup metrics."""
    resp = client.get("/api/battery/backup?load_kw=2.0&desired_hours=10.0")
    assert resp.status_code == 200
    data = resp.json()
    assert "capacity_kwh" in data
    assert "usable_energy_kwh" in data
    assert "expected_load_kw" in data
    assert "estimated_backup_hours" in data
    assert "ten_hour_backup_available" in data
    assert "backup_status" in data
    assert data["required_backup_hours"] == 10.0
