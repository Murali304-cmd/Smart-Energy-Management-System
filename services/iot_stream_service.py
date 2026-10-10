import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("SEMS.IoTStreamService")

class IoTStreamService:
    """
    WebSocket Live Telemetry Streamer & IoT Hardware Relay Controller.
    Manages active WebSocket client connections and relays for smart home devices.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        
        # Simulated connected IoT smart relays & meters
        self.iot_devices: Dict[str, Dict[str, Any]] = {
            "relay-ev": {
                "id": "relay-ev",
                "name": "Level-2 EV Charger",
                "type": "relay",
                "protocol": "MQTT / Tuya",
                "topic": "home/garage/ev_charger/set",
                "state": "OFF",
                "power_kw": 0.0,
                "max_power_kw": 3.3,
                "tier": "Tier 3 (Deferrable)",
                "last_toggle": datetime.now(timezone.utc).isoformat()
            },
            "relay-geyser": {
                "id": "relay-geyser",
                "name": "Solar Water Heater / Geyser",
                "type": "relay",
                "protocol": "Shelly 1PM",
                "topic": "shellies/shelly1pm-water/relay/0/command",
                "state": "OFF",
                "power_kw": 0.0,
                "max_power_kw": 2.0,
                "tier": "Tier 3 (Deferrable)",
                "last_toggle": datetime.now(timezone.utc).isoformat()
            },
            "relay-hvac": {
                "id": "relay-hvac",
                "name": "Inverter Dual AC (Living Room)",
                "type": "relay",
                "protocol": "Sonoff POW",
                "topic": "sonoff/hvac/power",
                "state": "ON",
                "power_kw": 1.4,
                "max_power_kw": 1.8,
                "tier": "Tier 2 (Modulatable)",
                "last_toggle": datetime.now(timezone.utc).isoformat()
            },
            "relay-washer": {
                "id": "relay-washer",
                "name": "Smart Washing Machine",
                "type": "relay",
                "protocol": "Zigbee / SmartPlug",
                "topic": "zigbee2mqtt/washer/set",
                "state": "OFF",
                "power_kw": 0.0,
                "max_power_kw": 1.2,
                "tier": "Tier 3 (Deferrable)",
                "last_toggle": datetime.now(timezone.utc).isoformat()
            },
            "meter-main": {
                "id": "meter-main",
                "name": "Bidirectional Smart Energy Meter",
                "type": "smart_meter",
                "protocol": "Modbus RTU / RS485",
                "topic": "meters/main/telemetry",
                "voltage_v": 230.2,
                "frequency_hz": 50.02,
                "grid_import_kw": 0.5,
                "grid_export_kw": 0.0,
                "status": "online"
            }
        }

    async def connect(self, websocket: WebSocket):
        """Accepts and registers a new WebSocket client connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Removes a disconnected WebSocket client."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Remaining active clients: {len(self.active_connections)}")

    async def broadcast_telemetry(self, telemetry_snapshot: Dict[str, Any]):
        """Broadcasts live telemetry payload to all active WebSocket clients."""
        if not self.active_connections:
            return

        payload_str = json.dumps({
            "type": "telemetry_stream",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": telemetry_snapshot
        })

        dead_connections = set()
        for conn in self.active_connections:
            try:
                await conn.send_text(payload_str)
            except Exception:
                dead_connections.add(conn)

        for dead in dead_connections:
            self.active_connections.discard(dead)

    def get_devices(self) -> List[Dict[str, Any]]:
        """Returns list of registered IoT relays and meters."""
        return list(self.iot_devices.values())

    def toggle_relay(self, device_id: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Toggles state of an IoT smart relay."""
        if device_id not in self.iot_devices:
            raise KeyError(f"IoT Device '{device_id}' not found.")

        dev = self.iot_devices[device_id]
        if dev.get("type") != "relay":
            raise ValueError(f"Device '{device_id}' is not a controllable relay.")

        new_state = state.upper() if state else ("OFF" if dev["state"] == "ON" else "ON")
        dev["state"] = new_state
        dev["power_kw"] = dev["max_power_kw"] if new_state == "ON" else 0.0
        dev["last_toggle"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"IoT Relay '{dev['name']}' ({device_id}) toggled to {new_state} ({dev['power_kw']} kW)")
        return dev
