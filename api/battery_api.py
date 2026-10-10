"""
SEMS Real Battery API Integration Layer
Supports: Enode API (OAuth2), Sandbox mode, and Demo mode.

Architecture:
    Browser -> FastAPI -> api/battery_api.py -> Enode -> Real Battery / Inverter
Strictly respects real telemetry without generating fake/invented values in REAL mode.
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
import requests

from config.settings import (
    BATTERY_MODE,
    ENODE_API_URL,
    ENODE_CLIENT_ID,
    ENODE_CLIENT_SECRET,
    ENODE_BATTERY_ID,
    ENODE_USER_ID,
    BATTERY_CAPACITY_KWH,
    BATTERY_MIN_SOC,
    BATTERY_MAX_SOC,
    BATTERY_CHARGE_EFFICIENCY,
    BATTERY_DISCHARGE_EFFICIENCY,
    BATTERY_MAX_CHARGE_KW,
    BATTERY_MAX_DISCHARGE_KW
)

logger = logging.getLogger("SEMS.BatteryAPI")


class BaseBatteryProvider(ABC):
    """Abstract interface for BESS / Inverter battery providers."""

    @property
    @abstractmethod
    def mode(self) -> str:
        """Returns provider mode name: 'real', 'sandbox', or 'demo'."""
        pass

    @abstractmethod
    def get_telemetry(self) -> Dict[str, Any]:
        """Fetches and returns normalized battery telemetry."""
        pass

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Checks provider connection and health status."""
        pass


class EnodeOAuth2Client:
    """Handles OAuth2 Client Credentials authentication flow with token caching and refresh."""

    def __init__(
        self,
        api_url: str = ENODE_API_URL,
        client_id: str = ENODE_CLIENT_ID,
        client_secret: str = ENODE_CLIENT_SECRET,
        timeout_seconds: float = 6.0
    ):
        self.api_url = (api_url or "").rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout_seconds = timeout_seconds
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.api_url)

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieves a valid OAuth2 bearer token. Caches token until 30s before expiration.
        Raises ValueError or requests.RequestException on failure.
        """
        if not self.is_configured():
            raise ValueError("Enode credentials not configured (ENODE_CLIENT_ID or ENODE_CLIENT_SECRET missing).")

        now = time.time()
        if not force_refresh and self._access_token and (now < self._expires_at - 30):
            return self._access_token

        token_endpoint = f"{self.api_url}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            resp = requests.post(
                token_endpoint,
                data=payload,
                headers=headers,
                timeout=self.timeout_seconds
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("access_token")
            expires_in = int(data.get("expires_in", 3600))
            if not token:
                raise ValueError("Enode OAuth2 token response did not contain access_token.")

            self._access_token = token
            self._expires_at = now + expires_in
            logger.info("Enode OAuth2 access token successfully acquired/refreshed.")
            return self._access_token
        except Exception as e:
            self._access_token = None
            self._expires_at = 0.0
            logger.error(f"Failed to authenticate with Enode OAuth2: {e}")
            raise


class EnodeBatteryProvider(BaseBatteryProvider):
    """
    Real Enode API Provider.
    Queries Enode battery system endpoints and returns normalized telemetry.
    Never produces fake values when real API is unreachable.
    """

    def __init__(
        self,
        api_url: str = ENODE_API_URL,
        client_id: str = ENODE_CLIENT_ID,
        client_secret: str = ENODE_CLIENT_SECRET,
        battery_id: str = ENODE_BATTERY_ID,
        user_id: str = ENODE_USER_ID,
        is_sandbox: bool = False
    ):
        self._is_sandbox = is_sandbox
        self.api_url = (api_url or "").rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.battery_id = battery_id
        self.user_id = user_id
        self.auth_client = EnodeOAuth2Client(
            api_url=self.api_url,
            client_id=self.client_id,
            client_secret=self.client_secret
        )

    @property
    def mode(self) -> str:
        return "sandbox" if self._is_sandbox else "real"

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Retrieves real-time telemetry from Enode.
        Returns normalized response. If API is down or battery disconnected,
        returns explicit unavailable status without fake values.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        current_mode = self.mode

        if not self.auth_client.is_configured():
            logger.warning(f"Enode credentials missing in {current_mode} mode.")
            return self._build_unavailable_response(
                mode=current_mode,
                error="Enode API credentials not configured in environment (.env)",
                timestamp=now_utc
            )

        try:
            token = self.auth_client.get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            # Select target endpoint
            if self.battery_id:
                url = f"{self.api_url}/battery-systems/{self.battery_id}"
            elif self.user_id:
                url = f"{self.api_url}/users/{self.user_id}/battery-systems"
            else:
                url = f"{self.api_url}/battery-systems"

            resp = requests.get(url, headers=headers, timeout=8.0)

            if resp.status_code in (401, 403):
                # Token might have expired early; try one refresh
                token = self.auth_client.get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {token}"
                resp = requests.get(url, headers=headers, timeout=8.0)

            if resp.status_code == 404:
                return self._build_unavailable_response(
                    mode=current_mode,
                    error=f"Battery system not found on Enode (ID: {self.battery_id or 'default'})",
                    timestamp=now_utc
                )

            resp.raise_for_status()
            raw_data = resp.json()

            # If response is a list, pick the first battery or matching ID
            target_device = raw_data
            if isinstance(raw_data, list):
                if not raw_data:
                    return self._build_unavailable_response(
                        mode=current_mode,
                        error="No battery systems linked to this Enode account.",
                        timestamp=now_utc
                    )
                target_device = raw_data[0]
            elif isinstance(raw_data, dict) and "data" in raw_data and isinstance(raw_data["data"], list):
                if not raw_data["data"]:
                    return self._build_unavailable_response(
                        mode=current_mode,
                        error="No battery systems found in Enode user account.",
                        timestamp=now_utc
                    )
                target_device = raw_data["data"][0]

            return self._normalize_enode_payload(target_device, current_mode, now_utc)

        except requests.Timeout:
            logger.error(f"Enode API request timed out in {current_mode} mode.")
            return self._build_unavailable_response(
                mode=current_mode,
                error="Battery API request timed out",
                timestamp=now_utc
            )
        except requests.RequestException as e:
            logger.error(f"Enode API network/HTTP failure: {e}")
            return self._build_unavailable_response(
                mode=current_mode,
                error=f"Battery API connection error: {str(e)}",
                timestamp=now_utc
            )
        except Exception as e:
            logger.error(f"Unexpected error retrieving Enode battery data: {e}", exc_info=True)
            return self._build_unavailable_response(
                mode=current_mode,
                error="Battery API unavailable",
                timestamp=now_utc
            )

    def _normalize_enode_payload(
        self,
        data: Dict[str, Any],
        mode: str,
        default_timestamp: str
    ) -> Dict[str, Any]:
        """Normalizes Enode raw device JSON into the standard SEMS schema."""
        battery_id = str(data.get("id", self.battery_id or "enode_battery"))

        # Model and Manufacturer extraction
        device_model = data.get("batteryModel") or data.get("model") or {}
        if isinstance(device_model, dict):
            manufacturer = device_model.get("brand") or device_model.get("manufacturer") or "Enode Compatible"
            model_name = device_model.get("model") or "BESS System"
        else:
            manufacturer = data.get("brand") or data.get("manufacturer") or "Enode Compatible"
            model_name = str(device_model) if device_model else "BESS System"

        # Connection & Reachability status
        is_reachable = data.get("isReachable", data.get("isConnected", True))
        if is_reachable is False:
            return {
                "mode": mode,
                "connected": False,
                "battery_id": battery_id,
                "manufacturer": manufacturer,
                "model": model_name,
                "soc_percent": None,
                "capacity_kwh": None,
                "available_energy_kwh": None,
                "battery_power_kw": None,
                "charge_power_kw": None,
                "discharge_power_kw": None,
                "status": "unavailable",
                "min_soc_percent": None,
                "max_soc_percent": None,
                "timestamp": default_timestamp,
                "error": "Battery device is currently offline / unreachable."
            }

        # SOC (State of Charge)
        charge_state = data.get("chargeState") or data.get("telemetry") or {}
        raw_soc = charge_state.get("batteryLevel", data.get("batteryLevel", data.get("stateOfCharge")))
        soc_percent = round(float(raw_soc), 1) if raw_soc is not None else None

        # Capacity (kWh)
        raw_cap = data.get("capacity", data.get("batteryCapacityKwh", BATTERY_CAPACITY_KWH))
        capacity_kwh = round(float(raw_cap), 2) if raw_cap is not None else None

        # Power (kW)
        raw_power = charge_state.get("powerKw", data.get("powerKw"))
        raw_charge_kw = charge_state.get("chargePowerKw", data.get("chargePowerKw"))
        raw_discharge_kw = charge_state.get("dischargePowerKw", data.get("dischargePowerKw"))

        battery_power_kw = round(float(raw_power), 3) if raw_power is not None else None

        if raw_charge_kw is not None:
            charge_power_kw = round(float(raw_charge_kw), 3)
        elif battery_power_kw is not None and battery_power_kw > 0.05:
            charge_power_kw = abs(battery_power_kw)
        else:
            charge_power_kw = 0.0

        if raw_discharge_kw is not None:
            discharge_power_kw = round(float(raw_discharge_kw), 3)
        elif battery_power_kw is not None and battery_power_kw < -0.05:
            discharge_power_kw = abs(battery_power_kw)
        else:
            discharge_power_kw = 0.0

        # Status: charging / discharging / idle
        raw_status = charge_state.get("isCharging", data.get("isCharging"))
        if raw_status is True or (charge_power_kw and charge_power_kw > 0.05):
            status = "charging"
        elif discharge_power_kw and discharge_power_kw > 0.05:
            status = "discharging"
        else:
            status = "idle"

        # Bounds & Usable Energy
        min_soc = float(data.get("minSoc", BATTERY_MIN_SOC))
        max_soc = float(data.get("maxSoc", BATTERY_MAX_SOC))

        if soc_percent is not None and capacity_kwh is not None:
            usable_fraction = max(0.0, (soc_percent - min_soc) / 100.0)
            available_energy_kwh = round(usable_fraction * capacity_kwh, 2)
        else:
            available_energy_kwh = None

        timestamp = data.get("lastSeen", data.get("timestamp", default_timestamp))

        return {
            "mode": mode,
            "connected": True,
            "battery_id": battery_id,
            "manufacturer": manufacturer,
            "model": model_name,
            "soc_percent": soc_percent,
            "capacity_kwh": capacity_kwh,
            "available_energy_kwh": available_energy_kwh,
            "battery_power_kw": battery_power_kw if battery_power_kw is not None else (charge_power_kw - discharge_power_kw),
            "charge_power_kw": charge_power_kw,
            "discharge_power_kw": discharge_power_kw,
            "status": status,
            "min_soc_percent": min_soc,
            "max_soc_percent": max_soc,
            "timestamp": timestamp,
            "error": None
        }

    def _build_unavailable_response(self, mode: str, error: str, timestamp: str) -> Dict[str, Any]:
        """Strict response format for unavailable real API data without inventing fake SOC."""
        return {
            "mode": mode,
            "connected": False,
            "battery_id": None,
            "manufacturer": None,
            "model": None,
            "soc_percent": None,
            "capacity_kwh": None,
            "available_energy_kwh": None,
            "battery_power_kw": None,
            "charge_power_kw": None,
            "discharge_power_kw": None,
            "status": "unavailable",
            "min_soc_percent": None,
            "max_soc_percent": None,
            "timestamp": timestamp,
            "error": error
        }

    def check_connection(self) -> Dict[str, Any]:
        """Verifies Enode authentication and endpoint health."""
        now_utc = datetime.now(timezone.utc).isoformat()
        if not self.auth_client.is_configured():
            return {
                "mode": self.mode,
                "connected": False,
                "api_status": "unconfigured",
                "battery_available": False,
                "last_update_time": now_utc,
                "error": "Enode credentials missing"
            }
        try:
            token = self.auth_client.get_access_token()
            return {
                "mode": self.mode,
                "connected": True,
                "api_status": "authenticated",
                "battery_available": True,
                "last_update_time": now_utc,
                "error": None
            }
        except Exception as e:
            return {
                "mode": self.mode,
                "connected": False,
                "api_status": "auth_failed",
                "battery_available": False,
                "last_update_time": now_utc,
                "error": str(e)
            }


class DemoBatteryProvider(BaseBatteryProvider):
    """
    Demo / Development Mode Provider.
    Only used when BATTERY_MODE=demo.
    Always explicitly marks mode as 'demo' to prevent misrepresentation.
    """

    def __init__(
        self,
        capacity_kwh: float = BATTERY_CAPACITY_KWH,
        min_soc: float = BATTERY_MIN_SOC,
        max_soc: float = BATTERY_MAX_SOC
    ):
        self.capacity_kwh = capacity_kwh
        self.min_soc = min_soc
        self.max_soc = max_soc

    @property
    def mode(self) -> str:
        return "demo"

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns standard normalized response labeled as DEMO mode."""
        now_utc = datetime.now(timezone.utc).isoformat()
        try:
            from energy.energy_state import get_energy_state_manager
            state = get_energy_state_manager().get_state()
            soc = float(state.get("battery_soc", 75.0))
            power = float(state.get("battery_power_kw", 0.0))
            mode_str = state.get("battery_mode", "idle")
            if "battery_capacity_kwh" in state and float(state["battery_capacity_kwh"]) > 0:
                self.capacity_kwh = float(state["battery_capacity_kwh"])
        except Exception:
            soc = 75.0
            power = 0.0
            mode_str = "idle"
            self.capacity_kwh = BATTERY_CAPACITY_KWH

        soc = max(self.min_soc, min(self.max_soc, soc))
        usable_fraction = max(0.0, (soc - self.min_soc) / 100.0)
        available_energy = round(usable_fraction * self.capacity_kwh, 2)

        charge_kw = abs(power) if mode_str == "charging" else 0.0
        discharge_kw = abs(power) if mode_str == "discharging" else 0.0

        return {
            "mode": "demo",
            "connected": True,
            "battery_id": "SUNGROW-TITAN-1000KWH-01",
            "manufacturer": "Sungrow Power Supply Co.",
            "model": "PowerTitan ST1000KWh Liquid-Cooled BESS (500 kW PCS)",
            "chemistry": "LiFePO4 (LFP) 314Ah Prismatic",
            "cooling_type": "Liquid Cooling (Glycol Loop)",
            "rated_cycles": 8000,
            "pcs_power_kw": 500.0,
            "soc_percent": round(soc, 1),
            "capacity_kwh": round(self.capacity_kwh, 2),
            "available_energy_kwh": available_energy,
            "battery_power_kw": round(charge_kw - discharge_kw, 3),
            "charge_power_kw": round(charge_kw, 3),
            "discharge_power_kw": round(discharge_kw, 3),
            "status": mode_str if mode_str in ("charging", "discharging") else "idle",
            "min_soc_percent": round(self.min_soc, 1),
            "max_soc_percent": round(self.max_soc, 1),
            "timestamp": now_utc,
            "error": None
        }

    def check_connection(self) -> Dict[str, Any]:
        return {
            "mode": "demo",
            "connected": True,
            "api_status": "demo_active",
            "battery_available": True,
            "last_update_time": datetime.now(timezone.utc).isoformat(),
            "error": None
        }


class BatteryClientFactory:
    """Factory to instantiate the appropriate provider according to BATTERY_MODE."""

    @staticmethod
    def get_provider(mode_override: Optional[str] = None) -> BaseBatteryProvider:
        mode = (mode_override or BATTERY_MODE or "demo").strip().lower()

        if mode == "real":
            return EnodeBatteryProvider(
                api_url=ENODE_API_URL,
                client_id=ENODE_CLIENT_ID,
                client_secret=ENODE_CLIENT_SECRET,
                battery_id=ENODE_BATTERY_ID,
                user_id=ENODE_USER_ID,
                is_sandbox=False
            )
        elif mode == "sandbox":
            sandbox_url = ENODE_API_URL or "https://enode-api.sandbox.enode.io"
            return EnodeBatteryProvider(
                api_url=sandbox_url,
                client_id=ENODE_CLIENT_ID,
                client_secret=ENODE_CLIENT_SECRET,
                battery_id=ENODE_BATTERY_ID,
                user_id=ENODE_USER_ID,
                is_sandbox=True
            )
        else:
            return DemoBatteryProvider(
                capacity_kwh=BATTERY_CAPACITY_KWH,
                min_soc=BATTERY_MIN_SOC,
                max_soc=BATTERY_MAX_SOC
            )


# Global singleton client instance
_battery_provider_instance: Optional[BaseBatteryProvider] = None

def get_battery_provider(mode_override: Optional[str] = None) -> BaseBatteryProvider:
    global _battery_provider_instance
    if mode_override is not None or _battery_provider_instance is None:
        return BatteryClientFactory.get_provider(mode_override)
    return _battery_provider_instance


def get_battery_telemetry(mode_override: Optional[str] = None) -> Dict[str, Any]:
    """Primary entry point to retrieve normalized battery telemetry."""
    provider = get_battery_provider(mode_override)
    return provider.get_telemetry()


def get_bess_telemetry(
    capacity_kwh: Optional[float] = None,
    min_soc: Optional[float] = None,
    max_soc: Optional[float] = None
) -> Dict[str, Any]:
    """
    Backward-compatible entry point for existing SEMS endpoints.
    Maps normalized battery telemetry to legacy BESS response while strictly
    adhering to real mode / unavailable handling.
    """
    telemetry = get_battery_telemetry()
    mode = telemetry.get("mode", "demo")
    connected = telemetry.get("connected", False)

    if not connected:
        return {
            "status": "unavailable",
            "mode": mode,
            "connected": False,
            "battery_soc": None,
            "battery_capacity_kwh": None,
            "battery_power_kw": None,
            "battery_mode": "unavailable",
            "available_battery_energy_kwh": None,
            "min_soc": min_soc or BATTERY_MIN_SOC,
            "max_soc": max_soc or BATTERY_MAX_SOC,
            "charge_efficiency": BATTERY_CHARGE_EFFICIENCY,
            "discharge_efficiency": BATTERY_DISCHARGE_EFFICIENCY,
            "max_charge_kw": BATTERY_MAX_CHARGE_KW,
            "max_discharge_kw": BATTERY_MAX_DISCHARGE_KW,
            "source": f"Enode ({mode.upper()})" if mode in ("real", "sandbox") else "SEMS-Demo",
            "timestamp": telemetry.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "error": telemetry.get("error", "Battery API unavailable")
        }

    soc = telemetry.get("soc_percent")
    cap = telemetry.get("capacity_kwh") or (capacity_kwh or BATTERY_CAPACITY_KWH)
    avail_energy = telemetry.get("available_energy_kwh")
    batt_status = telemetry.get("status") or "idle"
    batt_power = abs(telemetry.get("battery_power_kw") or 0.0)

    return {
        "status": "success",
        "mode": mode,
        "connected": True,
        "battery_soc": soc,
        "battery_capacity_kwh": cap,
        "battery_power_kw": batt_power,
        "battery_mode": batt_status,
        "available_battery_energy_kwh": avail_energy,
        "min_soc": telemetry.get("min_soc_percent", min_soc or BATTERY_MIN_SOC),
        "max_soc": telemetry.get("max_soc_percent", max_soc or BATTERY_MAX_SOC),
        "charge_efficiency": BATTERY_CHARGE_EFFICIENCY,
        "discharge_efficiency": BATTERY_DISCHARGE_EFFICIENCY,
        "max_charge_kw": BATTERY_MAX_CHARGE_KW,
        "max_discharge_kw": BATTERY_MAX_DISCHARGE_KW,
        "source": f"Enode ({mode.upper()})" if mode in ("real", "sandbox") else "SEMS-Demo",
        "timestamp": telemetry.get("timestamp", datetime.now(timezone.utc).isoformat())
    }
