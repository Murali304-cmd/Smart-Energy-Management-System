import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("SEMS.MQTTService")

class MQTTService:
    """
    Asynchronous MQTT Bridge with Home Assistant and ESPHome Auto-Discovery.
    Manages bi-directional MQTT pub/sub for smart meters, relays, and sensors.
    """

    def __init__(self, broker_host: str = "127.0.0.1", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.is_connected = False
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.discovered_entities: Dict[str, Dict[str, Any]] = {}
        self.virtual_broker_queue = asyncio.Queue()

    def generate_home_assistant_discovery_payload(
        self,
        device_id: str,
        device_name: str,
        component_type: str = "sensor",
        unit_of_measurement: str = "kW",
        device_class: str = "power"
    ) -> Dict[str, Any]:
        """Generates standard Home Assistant MQTT auto-discovery configuration packet."""
        return {
            "name": device_name,
            "unique_id": f"sems_{device_id}",
            "state_topic": f"homeassistant/{component_type}/sems/{device_id}/state",
            "device": {
                "identifiers": [f"sems_smart_energy_{device_id}"],
                "name": "Smart Home Energy Management System (SEMS)",
                "model": "SEMS-v2.0-AI",
                "manufacturer": "DeepMind SEMS",
                "sw_version": "2.4.0"
            },
            "unit_of_measurement": unit_of_measurement,
            "device_class": device_class,
            "value_template": "{{ value_json.value }}"
        }

    async def connect(self):
        """Initializes simulated or live MQTT connection."""
        self.is_connected = True
        logger.info(f"MQTT Service initialized (Connected to {self.broker_host}:{self.broker_port})")

    async def publish_telemetry(self, topic: str, payload: Dict[str, Any]):
        """Publishes live power state to MQTT broker."""
        msg = {
            "topic": topic,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.virtual_broker_queue.put(msg)
        logger.debug(f"MQTT Pub: {topic} -> {payload}")

    def register_ha_devices(self) -> List[Dict[str, Any]]:
        """Registers default Home Assistant entities for Solar, Battery, Grid, and Relays."""
        devices = [
            ("solar_generation", "Solar Power Generation", "sensor", "kW", "power"),
            ("home_load", "Home Power Consumption", "sensor", "kW", "power"),
            ("battery_soc", "Battery State of Charge", "sensor", "%", "battery"),
            ("grid_power", "Grid Import/Export", "sensor", "kW", "power"),
            ("ev_charger_switch", "EV Charger Relay", "switch", None, None),
            ("ac_switch", "HVAC Inverter AC Switch", "switch", None, None)
        ]
        registered = []
        for d_id, d_name, c_type, unit, d_class in devices:
            payload = self.generate_home_assistant_discovery_payload(d_id, d_name, c_type, unit, d_class)
            self.discovered_entities[d_id] = payload
            registered.append(payload)
        return registered

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_connected": self.is_connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "registered_entities": len(self.discovered_entities),
            "entities": list(self.discovered_entities.keys())
        }
