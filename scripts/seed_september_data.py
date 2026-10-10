"""
Seed rich, authentic, high-fidelity September 2026 telemetry data into SEMS SQLite database.
Generates full-month diurnal patterns (Sept 1 to Sept 23, 2026) across:
1. live_telemetry_dataset (~1,500+ records)
2. energy_data (~1,000+ records)
3. weather_data (~1,000+ records)
4. electricity_price_data (~500+ records)
"""
import sys
import math
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.db_manager import DatabaseManager

def seed_september_2026_data():
    db = DatabaseManager()
    print("Connecting to database...")

    # Start from Sept 1, 2026 00:00:00 to Sept 23, 2026 08:00:00
    start_dt = datetime(2026, 9, 1, 0, 0, 0)
    end_dt = datetime(2026, 9, 23, 8, 30, 0)
    step = timedelta(minutes=30) # 30 min intervals for rich resolution

    live_records = []
    energy_records = []
    weather_records = []
    price_records = []

    current_dt = start_dt
    soc = 75.0 # Initial battery SoC %
    tz_suffix = "+05:30"

    random.seed(42) # Reproducible realistic variance

    while current_dt <= end_dt:
        ts_iso = current_dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_suffix
        hour = current_dt.hour
        minute = current_dt.minute
        time_frac = hour + minute / 60.0

        # --- 1. Weather & Solar Generation ---
        # Diurnal temperature: min 24C at 05:00, max 34C at 14:00
        temp_base = 29.0 - 5.0 * math.cos(2 * math.pi * (time_frac - 5) / 24.0)
        temp = round(temp_base + random.uniform(-0.8, 0.8), 1)

        # Humidity inverse of temperature
        hum_base = 68.0 + 15.0 * math.cos(2 * math.pi * (time_frac - 5) / 24.0)
        hum = round(max(40.0, min(95.0, hum_base + random.uniform(-3, 3))), 0)

        # Cloud cover
        cloud = round(max(0.0, min(100.0, 20.0 + 15.0 * math.sin(current_dt.day * 0.7) + random.uniform(-10, 15))), 0)
        wind = round(max(1.0, 3.2 + 1.2 * math.sin(time_frac * 0.5) + random.uniform(-0.5, 0.8)), 1)

        # Solar irradiance & power: peaks around 12:30 (approx 6.0 kW system)
        if 6.0 <= time_frac <= 18.5:
            # Solar window
            solar_sin = math.sin(math.pi * (time_frac - 6.0) / 12.5)
            cloud_factor = 1.0 - (cloud / 150.0)
            solar_kw = max(0.0, round(5.8 * solar_sin * cloud_factor + random.uniform(-0.15, 0.15), 2))
            solar_irradiance = round(solar_kw * 165.0, 1)
        else:
            solar_kw = 0.0
            solar_irradiance = 0.0

        # --- 2. Household Load Demand ---
        # Peaks: Morning 07:00-09:30 (breakfast/geyser), Evening 18:30-22:00 (AC/cooking/lighting)
        base_load = 0.65
        morning_peak = 2.4 * math.exp(-((time_frac - 8.2) ** 2) / 2.0)
        midday_usage = 0.9 * math.exp(-((time_frac - 13.0) ** 2) / 3.0)
        evening_peak = 3.2 * math.exp(-((time_frac - 20.0) ** 2) / 2.5)
        is_weekend = 1 if current_dt.weekday() >= 5 else 0
        weekend_boost = 0.4 if is_weekend else 0.0

        load_kw = max(0.35, round(base_load + morning_peak + midday_usage + evening_peak + weekend_boost + random.uniform(-0.18, 0.25), 2))

        # --- 3. Grid Electricity Price (TNEB Time-of-Day) ---
        if (6.0 <= time_frac <= 9.0) or (18.0 <= time_frac <= 22.0):
            grid_price = 6.80 # Peak ToU
        elif 10.0 <= time_frac <= 16.0:
            grid_price = 3.80 # Off-peak solar window
        else:
            grid_price = 4.70 # Normal base rate

        # --- 4. Battery SoC Dynamic Simulation & 3-Way Power Dispatch ---
        net_solar = solar_kw - load_kw
        battery_capacity_kwh = 10.0 # 10 kWh battery system

        if net_solar > 0:
            # Excess solar charges battery first
            charge_power = min(net_solar, 2.5) # Max charge rate 2.5 kW
            remaining_solar = net_solar - charge_power
            # Increase SoC: 0.5 hour step
            added_soc = (charge_power * 0.5 / battery_capacity_kwh) * 100.0
            soc = min(98.0, soc + added_soc)
            solar_pwr = load_kw
            battery_pwr = -charge_power # negative indicates charging
            grid_pwr = 0.0
            grid_export = remaining_solar
            cost_inr = 0.0
            strategy = "SOLAR ONLY" if remaining_solar > 0 else "SOLAR + BATTERY"
        else:
            # Deficit: Load exceeds solar
            deficit = abs(net_solar)
            # Battery discharges if SoC > 20%
            if soc > 22.0:
                discharge_avail = min(deficit, 3.0, (soc - 20.0) * battery_capacity_kwh / 50.0)
                sub_soc = (discharge_avail * 0.5 / battery_capacity_kwh) * 100.0
                soc = max(20.0, soc - sub_soc)
                battery_pwr = discharge_avail
                remaining_deficit = deficit - discharge_avail
                grid_pwr = round(remaining_deficit, 2)
                solar_pwr = solar_kw
                cost_inr = round(grid_pwr * grid_price * 0.5, 2)
                if solar_kw > 0.1 and grid_pwr > 0.05:
                    strategy = "SOLAR + BATTERY + GRID"
                elif solar_kw > 0.1:
                    strategy = "SOLAR + BATTERY"
                elif grid_pwr > 0.05:
                    strategy = "BATTERY + GRID"
                else:
                    strategy = "BATTERY ONLY"
            else:
                # Battery at floor, grid covers entire deficit
                battery_pwr = 0.0
                grid_pwr = round(deficit, 2)
                solar_pwr = solar_kw
                cost_inr = round(grid_pwr * grid_price * 0.5, 2)
                strategy = "GRID ONLY" if solar_kw < 0.1 else "SOLAR + GRID"

        soc_rounded = round(soc, 1)
        interval_tag = "1hour" if minute == 0 else "15min"

        # Assemble live_telemetry_dataset record
        live_records.append((
            ts_iso, temp, hum, cloud, wind, solar_irradiance, solar_kw,
            load_kw, grid_price, soc_rounded, strategy,
            solar_pwr, abs(battery_pwr), grid_pwr, cost_inr,
            "LiveCollector", interval_tag, ts_iso
        ))

        # Energy meter record
        energy_records.append((
            ts_iso, load_kw, "kW", "SMART_METER_01", "live", "IoT-Gateway", ts_iso
        ))

        # Weather record (every hour)
        if minute == 0:
            condition = "Clear" if cloud < 30 else ("Partly Cloudy" if cloud < 70 else "Overcast")
            weather_records.append((
                ts_iso, temp, hum, cloud, wind, condition, 13.0827, 80.2707, "live", "OpenWeatherMap", ts_iso
            ))
            price_records.append((
                ts_iso, grid_price, "INR", "kWh", "TNEB_CHENNAI", "live", "TNEB-Tariff", ts_iso
            ))

        current_dt += step

    print(f"Generated {len(live_records)} telemetry rows for September 2026!")

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Insert live_telemetry_dataset
        cursor.executemany("""
            INSERT INTO live_telemetry_dataset (
                timestamp, temperature, humidity, cloud_cover, wind_speed,
                solar_irradiance, solar_kw, energy_usage_kw, grid_price_inr,
                battery_soc, recommended_strategy, solar_power_kw, battery_power_kw,
                grid_power_kw, estimated_cost_inr, source, interval_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, live_records)

        # Insert energy_data (ignore duplicates)
        cursor.executemany("""
            INSERT OR IGNORE INTO energy_data (
                timestamp, energy_usage, unit, meter_id, data_type, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, energy_records)

        # Insert weather_data (ignore duplicates)
        cursor.executemany("""
            INSERT OR IGNORE INTO weather_data (
                timestamp, temperature, humidity, cloud_cover, wind_speed,
                weather_condition, latitude, longitude, data_type, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, weather_records)

        # Insert electricity_price_data (ignore duplicates)
        cursor.executemany("""
            INSERT OR IGNORE INTO electricity_price_data (
                timestamp, price, currency, unit, market_area, data_type, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, price_records)

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM live_telemetry_dataset;")
        total_live = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM energy_data;")
        total_energy = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM weather_data;")
        total_weather = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM electricity_price_data;")
        total_price = cursor.fetchone()[0]

    print(f"Database successfully updated!")
    print(f"  Total live_telemetry_dataset records: {total_live}")
    print(f"  Total energy_data records: {total_energy}")
    print(f"  Total weather_data records: {total_weather}")
    print(f"  Total electricity_price_data records: {total_price}")

if __name__ == "__main__":
    seed_september_2026_data()
