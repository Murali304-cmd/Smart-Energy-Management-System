import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
from config.settings import DATABASE_PATH
logger = logging.getLogger('SEMS.DBManager')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def get_local_now_iso() -> str:
    return datetime.now().astimezone().isoformat()

def get_utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat()

def normalize_timestamp(ts_val: Any) -> Optional[str]:
    if ts_val is None:
        return None
    if isinstance(ts_val, (int, float)):
        try:
            return datetime.fromtimestamp(ts_val).astimezone().isoformat()
        except Exception:
            return None
    ts_str = str(ts_val).strip()
    if not ts_str:
        return None
    formats = ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
    local_tz = datetime.now().astimezone().tzinfo
    for fmt in formats:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=local_tz)
            return dt.isoformat()
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=local_tz)
        return dt.isoformat()
    except Exception:
        pass
    return ts_str

class DatabaseManager:

    def __init__(self, db_path: Path=DATABASE_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_tables()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON;')
        try:
            yield conn
        finally:
            conn.close()

    def init_tables(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n            CREATE TABLE IF NOT EXISTS weather_data (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                timestamp TEXT NOT NULL,\n                temperature REAL NOT NULL,\n                humidity REAL NOT NULL,\n                cloud_cover REAL,\n                wind_speed REAL,\n                weather_condition TEXT,\n                latitude REAL NOT NULL,\n                longitude REAL NOT NULL,\n                data_type TEXT NOT NULL,\n                source TEXT NOT NULL,\n                created_at TEXT NOT NULL,\n                CONSTRAINT uq_weather_record UNIQUE (source, timestamp, latitude, longitude)\n            );\n            ')
            cursor.execute('\n            CREATE TABLE IF NOT EXISTS energy_data (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                timestamp TEXT NOT NULL,\n                energy_usage REAL NOT NULL,\n                unit TEXT NOT NULL,\n                meter_id TEXT NOT NULL,\n                data_type TEXT NOT NULL,\n                source TEXT NOT NULL,\n                created_at TEXT NOT NULL,\n                CONSTRAINT uq_energy_record UNIQUE (source, timestamp, meter_id)\n            );\n            ')
            cursor.execute("\n            CREATE TABLE IF NOT EXISTS historical_tneb_data (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                original_record_id TEXT,\n                consumer_number TEXT,\n                billing_date TEXT,\n                previous_reading REAL,\n                current_reading REAL,\n                units_consumed REAL,\n                tariff_category TEXT,\n                bill_amount REAL,\n                due_date TEXT,\n                payment_status TEXT,\n                data_type TEXT NOT NULL DEFAULT 'historical',\n                source TEXT NOT NULL DEFAULT 'Kaggle-TNEB',\n                created_at TEXT NOT NULL,\n                CONSTRAINT uq_tneb_record UNIQUE (source, original_record_id)\n            );\n            ")
            cursor.execute('\n            CREATE TABLE IF NOT EXISTS electricity_price_data (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                timestamp TEXT NOT NULL,\n                price REAL NOT NULL,\n                currency TEXT NOT NULL,\n                unit TEXT NOT NULL,\n                market_area TEXT NOT NULL,\n                data_type TEXT NOT NULL,\n                source TEXT NOT NULL,\n                created_at TEXT NOT NULL,\n                CONSTRAINT uq_price_record UNIQUE (source, timestamp, market_area)\n            );\n            ')
            cursor.execute("\n            CREATE TABLE IF NOT EXISTS electricity_tariff_data (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                category TEXT NOT NULL,\n                slab_range TEXT NOT NULL,\n                rate_per_unit_inr REAL NOT NULL,\n                tax_rate_percent REAL NOT NULL,\n                notes TEXT,\n                data_type TEXT NOT NULL DEFAULT 'tariff',\n                source TEXT NOT NULL DEFAULT 'TNEB-Tariff-2026',\n                created_at TEXT NOT NULL,\n                CONSTRAINT uq_tariff UNIQUE (category, slab_range)\n            );\n            ")
            cursor.execute("\n            CREATE TABLE IF NOT EXISTS live_telemetry_dataset (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                timestamp TEXT NOT NULL,\n                temperature REAL NOT NULL,\n                humidity REAL NOT NULL,\n                cloud_cover REAL,\n                wind_speed REAL,\n                solar_irradiance REAL,\n                solar_kw REAL NOT NULL,\n                energy_usage_kw REAL NOT NULL,\n                grid_price_inr REAL NOT NULL,\n                battery_soc REAL NOT NULL,\n                recommended_strategy TEXT NOT NULL,\n                solar_power_kw REAL,\n                battery_power_kw REAL,\n                grid_power_kw REAL,\n                estimated_cost_inr REAL,\n                source TEXT NOT NULL DEFAULT 'LiveCollector',\n                interval_type TEXT NOT NULL DEFAULT '15min',\n                created_at TEXT NOT NULL\n            );\n            ")
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_ts ON weather_data(timestamp);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_ts ON energy_data(timestamp);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tneb_consumer ON historical_tneb_data(consumer_number);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_ts ON electricity_price_data(timestamp);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tariff_cat ON electricity_tariff_data(category);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_live_dataset_ts ON live_telemetry_dataset(timestamp);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_live_dataset_interval ON live_telemetry_dataset(interval_type);')
            conn.commit()

    def insert_weather(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        if not record:
            return (False, 'Empty weather record')
        ts = normalize_timestamp(record.get('timestamp'))
        if not ts:
            return (False, 'Missing or invalid timestamp')
        try:
            temp = float(record['temperature'])
            hum = float(record['humidity'])
            lat = float(record['latitude'])
            lon = float(record['longitude'])
        except (KeyError, TypeError, ValueError) as e:
            return (False, f'Validation failure on numeric coordinates or metrics: {e}')
        cloud = float(record['cloud_cover']) if record.get('cloud_cover') is not None else None
        wind = float(record['wind_speed']) if record.get('wind_speed') is not None else None
        condition = str(record.get('weather_condition', 'Unknown'))
        data_type = str(record.get('data_type', 'live'))
        source = str(record.get('source', 'OpenWeatherMap'))
        created_at = get_utc_now_iso()
        query = '\n        INSERT OR IGNORE INTO weather_data (\n            timestamp, temperature, humidity, cloud_cover, wind_speed,\n            weather_condition, latitude, longitude, data_type, source, created_at\n        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);\n        '
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (ts, temp, hum, cloud, wind, condition, lat, lon, data_type, source, created_at))
                conn.commit()
                if cursor.rowcount > 0:
                    return (True, 'Weather record stored')
                return (True, 'Duplicate weather record skipped (already exists)')
        except Exception as e:
            logger.error(f'Error inserting weather record: {e}')
            return (False, str(e))

    def insert_energy(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        if not record:
            return (False, 'Empty energy record')
        ts = normalize_timestamp(record.get('timestamp'))
        if not ts:
            return (False, 'Missing or invalid timestamp')
        try:
            usage = float(record['energy_usage'])
        except (KeyError, TypeError, ValueError) as e:
            return (False, f'Validation failure: energy_usage must be numeric ({e})')
        unit = str(record.get('unit', 'kW')).strip()
        meter_id = str(record.get('meter_id', 'METER001')).strip()
        data_type = str(record.get('data_type', 'live')).strip()
        source = str(record.get('source', 'SmartMeter')).strip()
        created_at = get_utc_now_iso()
        query = '\n        INSERT OR IGNORE INTO energy_data (\n            timestamp, energy_usage, unit, meter_id, data_type, source, created_at\n        ) VALUES (?, ?, ?, ?, ?, ?, ?);\n        '
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (ts, usage, unit, meter_id, data_type, source, created_at))
                conn.commit()
                if cursor.rowcount > 0:
                    return (True, 'Energy record stored')
                return (True, 'Duplicate energy record skipped (already exists)')
        except Exception as e:
            logger.error(f'Error inserting energy record: {e}')
            return (False, str(e))

    def insert_tneb_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        inserted_count = 0
        skipped_count = 0
        created_at = get_utc_now_iso()
        query = '\n        INSERT OR IGNORE INTO historical_tneb_data (\n            original_record_id, consumer_number, billing_date, previous_reading,\n            current_reading, units_consumed, tariff_category, bill_amount,\n            due_date, payment_status, data_type, source, created_at\n        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);\n        '
        valid_rows = []
        for idx, rec in enumerate(records):
            orig_id = str(rec.get('original_record_id') or f'TNEB_ROW_{idx + 1}').strip()
            consumer_no = str(rec.get('consumer_number') or '').strip()
            billing_date = normalize_timestamp(rec.get('billing_date'))

            def safe_float(val: Any) -> Optional[float]:
                if val is None or str(val).strip() == '':
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
            prev_read = safe_float(rec.get('previous_reading'))
            curr_read = safe_float(rec.get('current_reading'))
            units = safe_float(rec.get('units_consumed'))
            amount = safe_float(rec.get('bill_amount'))
            tariff = str(rec.get('tariff_category') or 'Domestic-1A').strip()
            due_date = str(rec.get('due_date') or '').strip()
            status = str(rec.get('payment_status') or 'Unknown').strip()
            valid_rows.append((orig_id, consumer_no, billing_date, prev_read, curr_read, units, tariff, amount, due_date, status, 'historical', 'Kaggle-TNEB', created_at))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for row in valid_rows:
                cursor.execute(query, row)
                if cursor.rowcount > 0:
                    inserted_count += 1
                else:
                    skipped_count += 1
            conn.commit()
        return {'inserted': inserted_count, 'skipped': skipped_count, 'invalid': 0, 'total_processed': len(records)}

    def insert_electricity_price(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        if not record:
            return (False, 'Empty electricity price record')
        ts = normalize_timestamp(record.get('timestamp'))
        if not ts:
            return (False, 'Missing or invalid timestamp')
        try:
            price = float(record['price'])
        except (KeyError, TypeError, ValueError) as e:
            return (False, f'Validation failure: price must be numeric ({e})')
        currency = str(record.get('currency', 'EUR')).strip()
        unit = str(record.get('unit', 'EUR/MWh')).strip()
        market_area = str(record.get('market_area', '10Y1001A1001A82H')).strip()
        data_type = str(record.get('data_type', 'live')).strip()
        source = str(record.get('source', 'ENTSO-E')).strip()
        created_at = get_utc_now_iso()
        query = '\n        INSERT OR IGNORE INTO electricity_price_data (\n            timestamp, price, currency, unit, market_area, data_type, source, created_at\n        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);\n        '
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (ts, price, currency, unit, market_area, data_type, source, created_at))
                conn.commit()
                if cursor.rowcount > 0:
                    return (True, 'Electricity price record stored')
                return (True, 'Duplicate electricity price record skipped (already exists)')
        except Exception as e:
            logger.error(f'Error inserting electricity price record: {e}')
            return (False, str(e))

    def insert_tariff_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        inserted_count = 0
        skipped_count = 0
        created_at = get_utc_now_iso()
        query = '\n        INSERT OR IGNORE INTO electricity_tariff_data (\n            category, slab_range, rate_per_unit_inr, tax_rate_percent, notes, data_type, source, created_at\n        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);\n        '
        valid_rows = []
        for rec in records:
            cat = str(rec.get('Category') or rec.get('category', '')).strip()
            slab = str(rec.get('Slab_Range') or rec.get('slab_range', '')).strip()
            try:
                rate = float(rec.get('Rate_Per_Unit_INR') or rec.get('rate_per_unit_inr', 0.0))
                tax = float(rec.get('Tax_Rate_Percent') or rec.get('tax_rate_percent', 0.0))
            except (ValueError, TypeError):
                continue
            notes = str(rec.get('Notes') or rec.get('notes', '')).strip()
            valid_rows.append((cat, slab, rate, tax, notes, 'tariff', 'TNEB-Tariff-2026', created_at))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for row in valid_rows:
                cursor.execute(query, row)
                if cursor.rowcount > 0:
                    inserted_count += 1
                else:
                    skipped_count += 1
            conn.commit()
        return {'inserted': inserted_count, 'skipped': skipped_count, 'total_processed': len(records)}

    def get_counts(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM weather_data;')
            weather_cnt = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM energy_data;')
            energy_cnt = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM historical_tneb_data;')
            tneb_cnt = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM electricity_price_data;')
            price_cnt = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM electricity_tariff_data;')
            tariff_cnt = cursor.fetchone()[0]
            return {'weather_records': weather_cnt, 'energy_records': energy_cnt, 'tneb_records': tneb_cnt, 'price_records': price_cnt, 'tariff_records': tariff_cnt}

    def get_latest_weather(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM weather_data ORDER BY id DESC LIMIT 1;')
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_energy(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM energy_data ORDER BY id DESC LIMIT 1;')
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_electricity_price(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM electricity_price_data ORDER BY id DESC LIMIT 1;')
            row = cursor.fetchone()
            return dict(row) if row else None

    def insert_live_dataset_record(self, record: Dict[str, Any]) -> int:
        """Inserts a single unified telemetry snapshot row into live_telemetry_dataset."""
        created_at = get_utc_now_iso()
        ts = normalize_timestamp(record.get('timestamp')) or created_at
        temp = float(record.get('temperature', 28.0))
        hum = float(record.get('humidity', 60.0))
        cloud = float(record.get('cloud_cover', 20.0)) if record.get('cloud_cover') is not None else 20.0
        wind = float(record.get('wind_speed', 3.0)) if record.get('wind_speed') is not None else 3.0
        irradiance = float(record.get('solar_irradiance', 0.0)) if record.get('solar_irradiance') is not None else 0.0
        solar_kw = float(record.get('solar_kw', 0.0))
        load_kw = float(record.get('energy_usage_kw', record.get('load_kw', 0.0)))
        price_inr = float(record.get('grid_price_inr', record.get('price_inr', 4.7)))
        battery_soc = float(record.get('battery_soc', 70.0))
        strategy = str(record.get('recommended_strategy', 'SOLAR ONLY'))
        solar_pwr = float(record.get('solar_power_kw', solar_kw))
        bat_pwr = float(record.get('battery_power_kw', 0.0))
        grid_pwr = float(record.get('grid_power_kw', 0.0))
        cost = float(record.get('estimated_cost_inr', record.get('cost_inr', 0.0)))
        source = str(record.get('source', 'LiveCollector'))
        interval_type = str(record.get('interval_type', '15min'))

        query = """
        INSERT INTO live_telemetry_dataset (
            timestamp, temperature, humidity, cloud_cover, wind_speed,
            solar_irradiance, solar_kw, energy_usage_kw, grid_price_inr,
            battery_soc, recommended_strategy, solar_power_kw, battery_power_kw,
            grid_power_kw, estimated_cost_inr, source, interval_type, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                ts, temp, hum, cloud, wind, irradiance, solar_kw, load_kw,
                price_inr, battery_soc, strategy, solar_pwr, bat_pwr,
                grid_pwr, cost, source, interval_type, created_at
            ))
            conn.commit()
            return cursor.lastrowid

    def get_live_dataset(
        self,
        limit: int = 100,
        offset: int = 0,
        interval_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetches live dataset rows with optional filtering and pagination."""
        params = []
        conditions = []

        if interval_filter and interval_filter.lower() not in ('all', ''):
            conditions.append("interval_type = ?")
            params.append(interval_filter.lower())

        if search and search.strip():
            s = f"%{search.strip()}%"
            conditions.append("(timestamp LIKE ? OR recommended_strategy LIKE ? OR source LIKE ?)")
            params.extend([s, s, s])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_query = f"SELECT COUNT(*) FROM live_telemetry_dataset {where_clause};"
        data_query = f"""
            SELECT * FROM live_telemetry_dataset
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?;
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]

            query_params = list(params) + [int(limit), int(offset)]
            cursor.execute(data_query, query_params)
            rows = [dict(r) for r in cursor.fetchall()]

            return {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "records": rows
            }

    def get_recent_stream_records(self, limit: int = 48) -> List[Dict[str, Any]]:
        """
        Fetches the latest telemetry records sorted in chronological ASCENDING order
        for smooth, continuous time-series trend plotting.
        """
        query = """
            SELECT * FROM (
                SELECT * FROM live_telemetry_dataset
                ORDER BY id DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC, id ASC;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (int(limit),))
            rows = [dict(r) for r in cursor.fetchall()]
            
            # Deduplicate records that have identical minute timestamps
            deduped = []
            seen_times = set()
            for r in rows:
                ts = r.get("timestamp", "")
                # Group by YYYY-MM-DDTHH:MM (ignoring millisecond duplicates)
                ts_key = ts[:16] if len(ts) >= 16 else ts
                if ts_key not in seen_times:
                    seen_times.add(ts_key)
                    deduped.append(r)
            return deduped

    def get_live_dataset_stats(self) -> Dict[str, Any]:
        """Calculates aggregate statistics for the live collected dataset."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM live_telemetry_dataset;")
            total_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM live_telemetry_dataset WHERE interval_type = '15min';")
            count_15min = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM live_telemetry_dataset WHERE interval_type = '1hour';")
            count_1hour = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM live_telemetry_dataset WHERE interval_type = 'manual';")
            count_manual = cursor.fetchone()[0]

            cursor.execute("""
                SELECT
                    AVG(solar_kw) as avg_solar,
                    AVG(energy_usage_kw) as avg_load,
                    AVG(battery_soc) as avg_soc,
                    AVG(estimated_cost_inr) as avg_cost,
                    MAX(timestamp) as last_collected
                FROM live_telemetry_dataset;
            """)
            agg = cursor.fetchone()

            return {
                "total_records": total_count,
                "count_15min": count_15min,
                "count_1hour": count_1hour,
                "count_manual": count_manual,
                "avg_solar_kw": round(float(agg['avg_solar'] or 0.0), 2),
                "avg_load_kw": round(float(agg['avg_load'] or 0.0), 2),
                "avg_soc": round(float(agg['avg_soc'] or 0.0), 1),
                "avg_cost_inr": round(float(agg['avg_cost'] or 0.0), 2),
                "last_collected": agg['last_collected']
            }

    def clear_live_dataset(self) -> bool:
        """Clears all records from the live collected telemetry dataset."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM live_telemetry_dataset;")
            conn.commit()
            return True

    def seed_initial_live_dataset_if_empty(self) -> int:
        """Seeds realistic historical samples (15min and 1hour intervals) if table is empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM live_telemetry_dataset;")
            count = cursor.fetchone()[0]
            if count > 0:
                return 0

        now = datetime.now()
        inserted = 0
        for i in range(96, 0, -1):
            t = now - timedelta(minutes=15 * i)
            hour_val = t.hour
            minute_val = t.minute
            interval_tag = "1hour" if minute_val == 0 else "15min"

            # Diurnal solar calculation
            if 6 <= hour_val <= 18:
                day_phase = (hour_val - 6 + minute_val / 60.0) / 12.0
                solar = round(3.8 * np.sin(day_phase * np.pi) * float(np.random.uniform(0.85, 1.05)), 2)
                irradiance = round(solar * 1000.0 / (3.0 * 0.85), 1)
            else:
                solar = 0.0
                irradiance = 0.0

            # Realistic load demand profile
            if 6 <= hour_val <= 9:
                base_l = 2.4
            elif 10 <= hour_val <= 16:
                base_l = 1.6
            elif 17 <= hour_val <= 22:
                base_l = 2.8
            else:
                base_l = 0.8
            load = round(base_l + float(np.random.uniform(-0.25, 0.35)), 2)
            load = max(0.4, load)

            price = 6.5 if (18 <= hour_val <= 22) else 4.7
            soc = round(float(np.clip(55.0 + 25.0 * np.sin((hour_val - 8) * np.pi / 12.0), 20.0, 95.0)), 1)
            temp = round(25.0 + 7.5 * np.sin(max(0, hour_val - 6) * np.pi / 12.0), 1)
            hum = round(max(35.0, min(88.0, 75.0 - 20.0 * np.sin(max(0, hour_val - 6) * np.pi / 12.0))), 1)

            # Strategy derivation
            if solar >= load:
                strategy = "SOLAR ONLY"
                solar_p = load
                bat_p = 0.0
                grid_p = 0.0
                cost = 0.0
            elif (solar + 1.5) >= load and soc > 30.0:
                strategy = "SOLAR + BATTERY"
                solar_p = solar
                bat_p = round(load - solar, 2)
                grid_p = 0.0
                cost = 0.0
            else:
                strategy = "SOLAR + BATTERY + GRID"
                solar_p = solar
                bat_p = round(min(1.2, max(0.0, (soc - 20.0) * 0.05)), 2)
                grid_p = round(max(0.0, load - solar_p - bat_p), 2)
                cost = round(grid_p * price, 2)

            self.insert_live_dataset_record({
                "timestamp": t.isoformat(),
                "temperature": temp,
                "humidity": hum,
                "cloud_cover": 20.0,
                "wind_speed": 3.4,
                "solar_irradiance": irradiance,
                "solar_kw": solar,
                "energy_usage_kw": load,
                "grid_price_inr": price,
                "battery_soc": soc,
                "recommended_strategy": strategy,
                "solar_power_kw": solar_p,
                "battery_power_kw": bat_p,
                "grid_power_kw": grid_p,
                "estimated_cost_inr": cost,
                "source": "OpenWeather+SmartMeter",
                "interval_type": interval_tag
            })
            inserted += 1

        return inserted

    def get_all_live_records(self, interval_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all live telemetry records ordered by timestamp descending for export."""
        params = []
        where_clause = ""
        if interval_filter and interval_filter.lower() not in ('all', ''):
            where_clause = "WHERE interval_type = ?"
            params.append(interval_filter.lower())

        query = f"SELECT * FROM live_telemetry_dataset {where_clause} ORDER BY id DESC;"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
