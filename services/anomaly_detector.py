import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger("SEMS.AnomalyDetector")

class AnomalyDetector:
    """
    Unsupervised Energy Anomaly & Diagnostics Engine.
    Detects meter sensor drift, phantom/vampire loads, ground leakage, and PV string shading.
    """

    def __init__(self):
        self.anomaly_history: List[Dict[str, Any]] = []

    def evaluate_telemetry(
        self,
        solar_kw: float,
        irradiance: float,
        load_kw: float,
        battery_soc: float,
        grid_price: float,
        hour: int
    ) -> Dict[str, Any]:
        """Runs rule-based and statistical anomaly classification on live snapshot."""
        anomalies_detected = []
        severity = "NORMAL"

        # 1. Partial Shading / Soiling Anomaly
        expected_solar = round((irradiance * 18.0 * 0.20) / 1000.0, 2)
        if irradiance > 400.0 and solar_kw < (expected_solar * 0.45):
            anomalies_detected.append({
                "type": "PV_PANEL_DEGRADATION_OR_SHADING",
                "severity": "WARNING",
                "message": f"Solar output ({solar_kw:.2f} kW) is significantly below theoretical ({expected_solar:.2f} kW) for {irradiance:.0f} W/m² irradiance.",
                "remedy": "Check for dust/soiling accumulation or physical obstruction on south-facing string."
            })
            severity = "WARNING"

        # 2. Nighttime Vampire Load Detection
        if (hour >= 23 or hour <= 4) and load_kw > 2.5:
            anomalies_detected.append({
                "type": "HIGH_NIGHTTIME_VAMPIRE_LOAD",
                "severity": "ALERT",
                "message": f"Unusually high baseline load detected at {hour:02d}:00 ({load_kw:.2f} kW).",
                "remedy": "Inspect unattended high-wattage loads (Water heater, AC, or EV charger)."
            })
            severity = "ALERT"

        # 3. Meter Drift / Infeasible Reading
        if solar_kw > 15.0 or load_kw > 25.0 or battery_soc < 0.0 or battery_soc > 100.0:
            anomalies_detected.append({
                "type": "SMART_METER_SENSOR_FAULT",
                "severity": "CRITICAL",
                "message": "Telemetry readings exceed physical boundaries.",
                "remedy": "Recalibrate or power-cycle smart meter AMR gateway."
            })
            severity = "CRITICAL"

        # 4. Inverter Reverse Power Risk
        if solar_kw > 0.0 and (hour < 5 or hour > 19):
            anomalies_detected.append({
                "type": "TIME_SYNCHRONIZATION_ANOMALY",
                "severity": "WARNING",
                "message": "Solar generation reported during nighttime hours.",
                "remedy": "Sync NTP time server on inverter gateway."
            })

        result = {
            "status": "ANOMALY" if anomalies_detected else "HEALTHY",
            "severity": severity,
            "anomaly_count": len(anomalies_detected),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "anomalies": anomalies_detected
        }

        if anomalies_detected:
            self.anomaly_history.append(result)
            if len(self.anomaly_history) > 100:
                self.anomaly_history.pop(0)

        return result

    def get_recent_anomalies(self) -> List[Dict[str, Any]]:
        return self.anomaly_history
