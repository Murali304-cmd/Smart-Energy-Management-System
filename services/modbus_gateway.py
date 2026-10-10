import logging
import struct
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("SEMS.ModbusGateway")

class ModbusGateway:
    """
    Industrial SunSpec Modbus TCP/RTU Gateway for Solar Inverters
    (Sungrow, SolarEdge, Fronius, Huawei, SMA) and Smart Bidirectional Energy Meters.
    """

    # SunSpec Standard Inverter Model Register Offsets (Model 101/103)
    SUNSPEC_MAP = {
        "AC_CURRENT": 40071,
        "AC_VOLTAGE": 40079,
        "AC_POWER_WATTS": 40083,
        "AC_FREQUENCY": 40085,
        "DC_POWER_WATTS": 40101,
        "CABINET_TEMP_C": 40103,
        "INVERTER_STATE": 40107,
        "TOTAL_ENERGY_WH": 40093
    }

    def __init__(self, host: str = "192.168.1.100", port: int = 502, slave_id: int = 1):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.is_online = True
        self.last_read_state: Dict[str, Any] = {}

    def read_inverter_registers(
        self,
        current_solar_kw: float,
        ambient_temp: float
    ) -> Dict[str, Any]:
        """
        Polls or simulates industrial SunSpec Modbus holding registers from the solar inverter.
        """
        watts = round(current_solar_kw * 1000.0, 1)
        voltage = 230.5
        current = round(watts / voltage, 2) if voltage > 0 else 0.0
        cabinet_temp = round(ambient_temp + 8.5, 1)

        raw_registers = {
            "reg_40071_current_a": current,
            "reg_40079_voltage_v": voltage,
            "reg_40083_active_power_w": watts,
            "reg_40085_freq_hz": 50.02,
            "reg_40101_dc_power_w": round(watts * 1.03, 1),
            "reg_40103_cabinet_temp_c": cabinet_temp,
            "reg_40107_inverter_status": 4 if watts > 0 else 1,  # 4 = MPPT Running, 1 = Standby
        }

        self.last_read_state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gateway": f"Modbus-TCP://{self.host}:{self.port} [Unit: {self.slave_id}]",
            "protocol": "SunSpec IEEE 1547 / Modbus TCP",
            "inverter_active_kw": current_solar_kw,
            "efficiency_pct": 97.4,
            "power_factor": 0.99,
            "registers": raw_registers
        }
        return self.last_read_state

    def get_gateway_info(self) -> Dict[str, Any]:
        return {
            "status": "connected" if self.is_online else "disconnected",
            "host": self.host,
            "port": self.port,
            "slave_id": self.slave_id,
            "protocol": "SunSpec Inverter Model 103 (Three Phase)",
            "last_read": self.last_read_state
        }
