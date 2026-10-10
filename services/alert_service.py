import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SEMS.AlertService")

class AlertService:
    """
    Multi-Channel Proactive Alert & Notification Dispatcher.
    Monitors hourly energy usage (solar, battery, grid), daily summary & reminders,
    battery SOC thresholds, blackout islanding mode, and peak tariff warnings.
    """

    def __init__(self):
        self.alerts: List[Dict[str, Any]] = [
            {
                "id": "alt-001",
                "severity": "info",
                "category": "hourly_usage",
                "title": "⚡ Hourly Energy Usage Update",
                "message": "Past hour consumption: ☀️ Solar: 3.20 kWh | 🔋 Battery: 1.10 kWh | ⚡ Grid: 0.50 kWh (Total: 4.80 kWh). Cost: ₹ 2.35.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_read": False,
                "action_url": "#tab-dashboard"
            },
            {
                "id": "alt-002",
                "severity": "success",
                "category": "daily_summary",
                "title": "📊 Daily Energy Summary & Budget Reminder",
                "message": "Today's Summary: ☀️ Solar: 18.50 kWh | 🔋 Battery: 6.20 kWh | ⚡ Grid: 2.80 kWh (Total: 27.50 kWh). Cost: ₹ 13.16 vs Budget ₹ 25.00 (Savings: ₹ 11.84). Clean share: 89.8%.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_read": False,
                "action_url": "#tab-dashboard"
            }
        ]

        self.notification_channels = {
            "web_dashboard": True,
            "browser_push": True,
            "telegram_bot": False,
            "email_alerts": False
        }

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Returns list of active system alerts."""
        return sorted(self.alerts, key=lambda x: x["timestamp"], reverse=True)

    def trigger_alert(
        self,
        severity: str,
        category: str,
        title: str,
        message: str,
        action_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates and broadcasts a new alert."""
        alert_obj = {
            "id": f"alt-{len(self.alerts) + 1:03d}",
            "severity": severity.lower(),  # info | warning | critical | success
            "category": category.lower(),
            "title": title,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_read": False,
            "action_url": action_url or "#tab-dashboard"
        }
        self.alerts.insert(0, alert_obj)
        logger.info(f"New [{severity.upper()}] alert generated: {title}")
        return alert_obj

    def record_hourly_usage(
        self,
        solar_kwh: float,
        battery_kwh: float,
        grid_kwh: float,
        total_kwh: float,
        cost_inr: float,
        hour: Optional[int] = None
    ) -> Dict[str, Any]:
        """Creates hourly breakdown notification of power used across solar, battery, grid."""
        h_str = f"{hour:02d}:00" if hour is not None else datetime.now().strftime("%H:00")
        title = f"⚡ Hourly Energy Usage ({h_str})"
        message = (
            f"Past hour power used: ☀️ Solar: {solar_kwh:.2f} kWh | "
            f"🔋 Battery: {battery_kwh:.2f} kWh | "
            f"⚡ Utility Grid: {grid_kwh:.2f} kWh (Total: {total_kwh:.2f} kWh). "
            f"Cost incurred: ₹ {cost_inr:.2f}."
        )
        return self.trigger_alert(
            severity="info",
            category="hourly_usage",
            title=title,
            message=message,
            action_url="#tab-dashboard"
        )

    def record_daily_summary(
        self,
        solar_kwh: float,
        battery_kwh: float,
        grid_kwh: float,
        total_kwh: float,
        cost_inr: float,
        budget_inr: float,
        savings_inr: float,
        clean_pct: float
    ) -> Dict[str, Any]:
        """Creates daily summary notification and budget reminder."""
        title = "📊 Daily Energy Summary & Budget Reminder"
        message = (
            f"Today's Energy Summary: ☀️ Solar: {solar_kwh:.2f} kWh | "
            f"🔋 Battery: {battery_kwh:.2f} kWh | "
            f"⚡ Grid: {grid_kwh:.2f} kWh (Total: {total_kwh:.2f} kWh). "
            f"Cost: ₹ {cost_inr:.2f} vs Budget ₹ {budget_inr:.2f} (Savings: ₹ {savings_inr:.2f}). "
            f"Clean Energy Share: {clean_pct:.1f}%."
        )
        return self.trigger_alert(
            severity="success",
            category="daily_summary",
            title=title,
            message=message,
            action_url="#tab-dashboard"
        )

    def evaluate_live_conditions(
        self,
        battery_soc: float,
        is_grid_outage: bool = False,
        current_solar_kw: float = 0.0,
        predicted_solar_kw: float = 0.0,
        current_load_kw: float = 1.5,
        predicted_load_kw: float = 1.5,
        price_inr: float = 4.70,
        grid_power_kw: float = 0.0,
        hour: int = 12,
        unsafe_rejected: bool = False,
        rejection_reason: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluates system telemetry across the 7 mandated alert categories (Goal 12):
        1. Low battery SoC
        2. High electricity price
        3. High predicted load
        4. Low solar generation
        5. Excess solar generation
        6. Grid dependency
        7. Battery safety conditions
        """
        generated = []

        # 1. Low battery SoC Alert (< 25% warning, <= 20% critical)
        if battery_soc <= 20.0:
            if not any(a["category"] == "low_battery_critical" and not a["is_read"] for a in self.alerts):
                alert = self.trigger_alert(
                    severity="critical",
                    category="low_battery_critical",
                    title="⚠️ Critical Low Battery SoC",
                    message=f"Battery SoC is at {battery_soc:.1f}% (Minimum cutoff reached). Discharge halted to protect battery health."
                )
                generated.append(alert)
        elif battery_soc <= 25.0:
            if not any(a["category"] == "low_battery_warning" and not a["is_read"] for a in self.alerts):
                alert = self.trigger_alert(
                    severity="warning",
                    category="low_battery_warning",
                    title="🔋 Low Battery Warning",
                    message=f"Battery SoC is low at {battery_soc:.1f}%. Consider reducing heavy appliance consumption."
                )
                generated.append(alert)

        # 2. High Electricity Price Alert (>= ₹6.0/unit)
        if price_inr >= 6.0:
            if not any(a["category"] == "high_price" and not a["is_read"] for a in self.alerts):
                alert = self.trigger_alert(
                    severity="warning",
                    category="high_price",
                    title="📈 High Peak Tariff Active",
                    message=f"Current electricity price is ₹{price_inr:.2f}/kWh. Peak shaving dispatch activated to minimize grid cost."
                )
                generated.append(alert)

        # 3. High Predicted Load Alert (> 3.5 kW)
        if predicted_load_kw > 3.5 or current_load_kw > 3.5:
            if not any(a["category"] == "high_load" and not a["is_read"] for a in self.alerts):
                alert = self.trigger_alert(
                    severity="warning",
                    category="high_load",
                    title="⚡ High Energy Demand Forecast",
                    message=f"Predicted peak load is {max(predicted_load_kw, current_load_kw):.2f} kW. SEMS is pre-allocating ESS capacity."
                )
                generated.append(alert)

        # 4. Low Solar Generation during Daylight Hours (< 0.5 kW between 08:00 and 16:00)
        if 8 <= hour <= 16 and (current_solar_kw < 0.5 or predicted_solar_kw < 0.5):
            if not any(a["category"] == "low_solar" and not a["is_read"] for a in self.alerts):
                alert = self.trigger_alert(
                    severity="info",
                    category="low_solar",
                    title="☁️ Low Solar Irradiance Detected",
                    message=f"Solar generation is low ({current_solar_kw:.2f} kW) due to cloud cover. Supplementary sources scheduled."
                )
                generated.append(alert)

        # 5. Excess Solar Generation (Surplus > 1.5 kW after load)
        if current_solar_kw > current_load_kw + 1.5:
            if not any(a["category"] == "excess_solar" and not a["is_read"] for a in self.alerts):
                surplus = current_solar_kw - current_load_kw
                alert = self.trigger_alert(
                    severity="success",
                    category="excess_solar",
                    title="☀️ Excess Solar Generation",
                    message=f"Surplus solar generation of {surplus:.2f} kW available. Charging battery and exporting via Net-Metering."
                )
                generated.append(alert)

        # 6. Grid Dependency Alert (Grid power supplies > 70% of load)
        if current_load_kw > 0.5 and (grid_power_kw / current_load_kw) > 0.70:
            if not any(a["category"] == "grid_dependency" and not a["is_read"] for a in self.alerts):
                dep_pct = (grid_power_kw / current_load_kw) * 100.0
                alert = self.trigger_alert(
                    severity="info",
                    category="grid_dependency",
                    title="🔌 Elevated Grid Dependency",
                    message=f"Utility grid is supplying {dep_pct:.1f}% ({grid_power_kw:.2f} kW) of demand."
                )
                generated.append(alert)

        # 7. Battery Safety Conditions Alert
        if unsafe_rejected or battery_soc >= 100.0 or battery_soc <= 20.0:
            reason = rejection_reason or "Battery physical threshold interlock activated."
            if not any(a["category"] == "battery_safety" and not a["is_read"] for a in self.alerts):
                alert = self.trigger_alert(
                    severity="critical" if battery_soc <= 20.0 else "warning",
                    category="battery_safety",
                    title="🛡️ Battery Safety Interlock Engaged",
                    message=f"Constraint Guard: {reason}"
                )
                generated.append(alert)

        return generated

    def dismiss_alert(self, alert_id: str) -> bool:
        """Marks an alert as read or dismissed."""
        for a in self.alerts:
            if a["id"] == alert_id:
                a["is_read"] = True
                return True
        return False

    def mark_all_read(self) -> int:
        """Marks all alerts as read."""
        count = 0
        for a in self.alerts:
            if not a.get("is_read"):
                a["is_read"] = True
                count += 1
        return count

    def clear_all_alerts(self) -> int:
        """Clears all alerts."""
        count = len(self.alerts)
        self.alerts.clear()
        return count

