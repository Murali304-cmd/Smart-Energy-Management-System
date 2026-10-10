# Smart Energy Management System (SEMS) 🔋☀️⚡

An AI-driven Smart Home Energy Management System with **Real Battery API (Enode)** integration, XGBoost tariff prediction, MLP solar forecasting, LSTM load forecasting, Deep Q-Network (DQN) decision-making, and Explainable AI (XAI).

---

## 🏗️ System Architecture

```text
TNEB Historical Dataset ───► Preprocessing ───► XGBoost (Electricity Price Prediction)
OpenWeatherMap API       ───► Preprocessing ───► MLP (Solar Generation Prediction)
Smart Meter / IoT API   ───► Preprocessing ───► LSTM (Household Load Prediction)
REAL BATTERY API (Enode) ───► BESS Telemetry ─► DQN Smart Decision ──► Energy Allocator ──► XAI ──► FastAPI ──► Dashboard UI
```

---

## ⚡ Energy Flow & Physical Hierarchy

SEMS strictly enforces the physical energy hierarchy:
1. **☀️ Solar $\rightarrow$ 🏠 Load**: Solar generation always serves household load first.
2. **Excess Solar $\rightarrow$ 🔋 Battery**: Surplus solar charges the battery storage (up to `MAX_SOC` and charge power limits).
3. **Excess Solar $\rightarrow$ ⚡ Grid Export**: If the battery reaches capacity, excess solar exports to the grid.
4. **🔋 Battery $\rightarrow$ 🏠 Load**: When solar is insufficient, the battery discharges to cover unmet load (down to `MIN_SOC`).
5. **⚡ Grid Import $\rightarrow$ 🏠 Load**: The utility grid supplies only the remaining deficit.

### ⚖️ Energy Balance Verification
Every allocation cycle validates:
$$\text{Solar} + \text{Battery Discharge} + \text{Grid Import} \approx \text{Household Load} + \text{Battery Charge} + \text{Grid Export}$$

---

## 🔋 Battery API Integration (Enode)

### Supported Operational Modes
Configure `BATTERY_MODE` in `.env`:

| Mode | Description | Mode Badge in Dashboard |
| :--- | :--- | :--- |
| `real` | Communicates directly with Enode OAuth2 and connected hardware BESS / Inverters. Returns explicit `status: "unavailable"` and `connected: false` if unreachable. **Never produces fake SOC.** | `REAL BATTERY DATA` |
| `sandbox` | Communicates with Enode Sandbox test environment. | `SANDBOX BATTERY DATA` |
| `demo` | Simulated virtual battery telemetry for local development. | `DEMO BATTERY DATA` |

---

## 🚀 Environment Configuration (`.env`)

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Battery API Mode: real | sandbox | demo
BATTERY_MODE=demo

# Enode Credentials (https://developers.enode.com/)
ENODE_API_URL=https://enode-api.production.enode.io
ENODE_CLIENT_ID=your_enode_client_id_here
ENODE_CLIENT_SECRET=your_enode_client_secret_here
ENODE_BATTERY_ID=your_enode_battery_id_here
ENODE_USER_ID=your_enode_user_id_here
BATTERY_POLL_INTERVAL_SECONDS=15

# Battery Physical Parameters
BATTERY_CAPACITY_KWH=20.0
BATTERY_MIN_SOC=20.0
BATTERY_MAX_SOC=100.0
BATTERY_CHARGE_EFFICIENCY=0.95
BATTERY_DISCHARGE_EFFICIENCY=0.95
BATTERY_MAX_CHARGE_KW=5.0
BATTERY_MAX_DISCHARGE_KW=5.0
DESIRED_BACKUP_HOURS=10.0
```

> [!CAUTION]
> Never commit `.env` containing live secrets. `.env` is listed in `.gitignore`.

---

## 🔌 FastAPI Endpoints

### 1. `GET /api/battery`
Returns normalized battery information:
```json
{
  "mode": "real",
  "connected": true,
  "battery_id": "batt_enode_01",
  "manufacturer": "Tesla / Enphase / SolarEdge",
  "model": "Powerwall 2",
  "soc_percent": 68.0,
  "capacity_kwh": 20.0,
  "available_energy_kwh": 13.6,
  "battery_power_kw": -2.0,
  "charge_power_kw": 0.0,
  "discharge_power_kw": 2.0,
  "status": "discharging",
  "min_soc_percent": 20.0,
  "max_soc_percent": 100.0,
  "timestamp": "2026-09-12T06:30:00Z",
  "error": null
}
```

### 2. `GET /api/battery/status`
Returns connection health and availability:
```json
{
  "mode": "real",
  "connected": true,
  "connection_status": "connected",
  "battery_availability": true,
  "api_status": "authenticated",
  "status": "discharging",
  "last_update_time": "2026-09-12T06:30:00Z",
  "error": null
}
```

### 3. `GET /api/battery/backup`
Computes non-hardcoded backup metrics based on dynamic load:
```json
{
  "capacity_kwh": 20.0,
  "usable_energy_kwh": 9.12,
  "available_energy_kwh": 9.6,
  "expected_load_kw": 1.8,
  "estimated_backup_hours": 5.1,
  "required_backup_hours": 10.0,
  "ten_hour_backup_available": false,
  "backup_status": "10-hour backup not available",
  "status_label": "10-Hour Backup Not Available (5.1h estimated vs 10.0h target)"
}
```

---

## 🧮 10-Hour Backup Calculation Formula

$$\text{usable\_energy\_kwh} = \text{battery\_capacity\_kwh} \times \frac{\text{SOC} - \text{MIN\_SOC}}{100} \times \eta_{\text{discharge}}$$

$$\text{backup\_hours} = \frac{\text{usable\_energy\_kwh}}{\text{household\_load\_kw}}$$

- If $\text{backup\_hours} \ge 10.0 \implies$ `"10-hour backup available"`, `ten_hour_backup_available = True`
- If $\text{backup\_hours} < 10.0 \implies$ `"10-hour backup not available"`, `ten_hour_backup_available = False`

---

## 🧪 Testing

Run test suites:
```powershell
python -m pytest tests/test_battery_api.py tests/test_battery_manager.py -v
python -m pytest
```

---

## 🖥️ Running the Application

1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Start the FastAPI server:
   ```powershell
   uvicorn server:app --reload --port 8000
   ```
3. Open `http://localhost:8000` in your web browser.

