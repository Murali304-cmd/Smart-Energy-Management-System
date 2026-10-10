"""
SEMS Live Real-Time Solar & Weather Nowcasting Service.

Connects to Open-Meteo Solar Radiation API (no API key required)
to retrieve live Global Horizontal Irradiance (GHI), Direct Normal Irradiance (DNI),
cloud cover %, and ambient temperature with in-memory caching and offline fallback.
"""

import time
import math
import logging
import urllib.request
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.WeatherService")

OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"


class WeatherService:
    def __init__(self, lat: float = 13.0827, lon: float = 80.2707, cache_ttl_seconds: int = 900):
        self.lat = lat
        self.lon = lon
        self.cache_ttl = cache_ttl_seconds
        self._cached_data: Optional[Dict[str, Any]] = None
        self._last_fetch_time: float = 0.0

    def _fetch_from_open_meteo(self) -> Dict[str, Any]:
        """Fetches live meteorological and solar irradiance telemetry from Open-Meteo."""
        url = (
            f"{OPEN_METEO_API}?latitude={self.lat}&longitude={self.lon}"
            "&current=temperature_2m,relative_humidity_2m,cloud_cover,is_day"
            "&hourly=temperature_2m,cloud_cover,direct_normal_irradiance,shortwave_radiation"
            "&timezone=auto&forecast_days=1"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SEMS-Solar-Monitor/2.5"}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            raise RuntimeError(f"Open-Meteo returned status {response.status}")

    def _generate_synthetic_weather(self, hour: int) -> Dict[str, Any]:
        """Physics-based fallback solar model when internet/API is offline."""
        # Diurnal solar bell curve between 06:00 and 18:00
        if 6 <= hour <= 18:
            sun_angle = math.sin((hour - 6) / 12.0 * math.pi)
            ghi = max(0.0, round(950.0 * sun_angle, 1))
            dni = max(0.0, round(820.0 * sun_angle, 1))
            temp = round(28.0 + (7.0 * sun_angle), 1)
            is_day = 1
        else:
            ghi = 0.0
            dni = 0.0
            temp = 25.5
            is_day = 0

        cloud_cover = 18.0
        return {
            "source": "physics_simulation_fallback",
            "current": {
                "temperature_2m": temp,
                "relative_humidity_2m": 65.0,
                "cloud_cover": cloud_cover,
                "is_day": is_day,
                "global_horizontal_irradiance": ghi,
                "direct_normal_irradiance": dni
            },
            "hourly": {
                "time": [f"{h:02d}:00" for h in range(24)],
                "global_horizontal_irradiance": [
                    max(0.0, round(950.0 * math.sin((h - 6) / 12.0 * math.pi), 1)) if 6 <= h <= 18 else 0.0
                    for h in range(24)
                ],
                "cloud_cover": [18.0] * 24,
                "temperature_2m": [round(26.0 + 6.0 * max(0.0, math.sin((h - 6) / 12.0 * math.pi)), 1) for h in range(24)]
            }
        }

    def get_weather_data(self) -> Dict[str, Any]:
        """Returns cached or freshly fetched weather telemetry."""
        now = time.time()
        if self._cached_data and (now - self._last_fetch_time < self.cache_ttl):
            return self._cached_data

        try:
            raw = self._fetch_from_open_meteo()
            # Normalize and augment current readings with irradiance from current or hourly
            curr = raw.get("current", {})
            hourly = raw.get("hourly", {})

            current_hour = datetime.now().hour
            ghi_hourly = hourly.get("shortwave_radiation", hourly.get("global_horizontal_irradiance", []))
            dni_hourly = hourly.get("direct_normal_irradiance", [])

            ghi = ghi_hourly[current_hour] if current_hour < len(ghi_hourly) else 0.0
            dni = dni_hourly[current_hour] if current_hour < len(dni_hourly) else 0.0

            processed = {
                "source": "open_meteo_live",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latitude": self.lat,
                "longitude": self.lon,
                "current": {
                    "temperature_c": curr.get("temperature_2m", 30.0),
                    "relative_humidity_pct": curr.get("relative_humidity_2m", 60.0),
                    "cloud_cover_pct": curr.get("cloud_cover", 20.0),
                    "is_day": curr.get("is_day", 1),
                    "ghi_wm2": float(ghi),
                    "dni_wm2": float(dni)
                },
                "hourly_forecast": {
                    "time": hourly.get("time", [])[:24],
                    "ghi_wm2": ghi_hourly[:24],
                    "cloud_cover_pct": hourly.get("cloud_cover", [])[:24],
                    "temperature_c": hourly.get("temperature_2m", [])[:24]
                }
            }
            self._cached_data = processed
            self._last_fetch_time = now
            return processed

        except Exception as e:
            logger.warning(f"Unable to fetch live Open-Meteo weather ({e}). Falling back to simulation model.")
            hour = datetime.now().hour
            sim = self._generate_synthetic_weather(hour)
            sim["timestamp"] = datetime.now(timezone.utc).isoformat()
            sim["latitude"] = self.lat
            sim["longitude"] = self.lon
            self._cached_data = sim
            self._last_fetch_time = now
            return sim

    def estimate_solar_generation_kw(self, panel_capacity_kw: float = 4.0, system_efficiency: float = 0.82) -> float:
        """
        Estimates real-time solar panel output in kW using Photovoltaic temperature
        derating and Global Horizontal Irradiance (GHI).
        Formula: P = Capacity * (GHI / 1000) * Efficiency * (1 - temp_coeff * (T_cell - 25))
        """
        data = self.get_weather_data()
        curr = data.get("current", {})
        ghi = float(curr.get("ghi_wm2", curr.get("global_horizontal_irradiance", 0.0)) or 0.0)
        temp_c = float(curr.get("temperature_c", curr.get("temperature_2m", 25.0)) or 25.0)

        if ghi <= 5.0:
            return 0.0

        # Cell temperature calculation based on NOCT standard
        cell_temp = temp_c + (ghi / 800.0) * (45.0 - 20.0)
        temp_loss = max(0.0, (cell_temp - 25.0) * 0.004)  # 0.4% loss per degree above 25C
        derating = max(0.65, 1.0 - temp_loss)

        pv_kw = panel_capacity_kw * (ghi / 1000.0) * system_efficiency * derating
        return round(float(pv_kw), 3)


# Singleton
weather_service = WeatherService()
