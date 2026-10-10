import json
import urllib.request
import logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SEMS.FetchSolar")

BASE_DIR = Path(__file__).resolve().parent.parent
HISTORICAL_DIR = BASE_DIR / "data" / "historical"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def fetch_and_process_historical_solar():
    # Chennai coordinates: 13.0827° N, 80.2707° E
    # Fetch 8 months of authentic GHI, DNI, DHI, cloud cover, temperature, humidity, wind
    start_date = "2024-01-01"
    end_date = "2024-08-31"
    
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude=13.0827&longitude=80.2707"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly=temperature_2m,relative_humidity_2m,cloud_cover,shortwave_radiation,direct_normal_irradiance,diffuse_radiation,wind_speed_10m"
        f"&timezone=Asia%2FKolkata"
    )
    
    logger.info(f"Fetching authentic solar/weather archive data from Open-Meteo for {start_date} to {end_date}...")
    req = urllib.request.Request(url, headers={"User-Agent": "SEMS-SmartEnergyResearch/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_json = json.loads(resp.read().decode("utf-8"))
    
    hourly = raw_json["hourly"]
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(hourly["time"]),
        "temperature": hourly["temperature_2m"],
        "humidity": hourly["relative_humidity_2m"],
        "cloud_cover": hourly["cloud_cover"],
        "shortwave_radiation": hourly["shortwave_radiation"], # GHI in W/m²
        "direct_normal_irradiance": hourly["direct_normal_irradiance"], # DNI in W/m²
        "diffuse_radiation": hourly["diffuse_radiation"], # DHI in W/m²
        "wind_speed": hourly["wind_speed_10m"]
    })
    
    # Solar irradiance target: shortwave_radiation (GHI in W/m²)
    # Also provide solar_irradiance (primary) and solar_irradiance_proxy for backwards compatibility
    df["solar_irradiance"] = df["shortwave_radiation"].clip(lower=0.0)
    df["solar_irradiance_proxy"] = df["solar_irradiance"] # replace synthetic proxy with authentic physical GHI!
    
    # Feature Engineering
    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.day
    df["month"] = df["timestamp"].dt.month
    df["weekday"] = df["timestamp"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    
    # Cyclic time encoding
    df["sin_hour"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["cos_hour"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["sin_month"] = np.sin(2 * np.pi * df["month"] / 12.0)
    df["cos_month"] = np.cos(2 * np.pi * df["month"] / 12.0)
    
    # Solar zenith / daytime mask:
    # In Chennai (~13°N), daylight is approximately 06:00 to 18:00 IST
    # Strictly mask night hours where solar irradiance is physically 0
    df["is_daylight"] = ((df["hour"] >= 6) & (df["hour"] <= 18)).astype(int)
    
    # Heat index and degree metrics
    t = df["temperature"]
    rh = df["humidity"]
    df["heat_index"] = 0.5 * (t + 61.0 + ((t - 68.0) * 1.2) + (rh * 0.094))
    df["cooling_degree_metric"] = np.maximum(0.0, t - 24.0)
    df["heating_degree_metric"] = np.maximum(0.0, 18.0 - t)
    
    # Solar generation estimate in kW for a 5 kWp rooftop PV array:
    # P_solar (kW) = GHI (W/m²) / 1000 * Array_Capacity (5 kWp) * System_Efficiency (0.82)
    df["solar_generation_kw"] = np.round((df["solar_irradiance"] / 1000.0) * 5.0 * 0.82, 3)
    
    # Fill any nulls with forward/backward fill
    df = df.bfill().ffill()
    
    # Save to historical
    hist_file = HISTORICAL_DIR / "solar_weather_chennai_2024.csv"
    df.to_csv(hist_file, index=False)
    logger.info(f"Saved {len(df)} authentic historical solar rows to {hist_file}")
    
    # Save to processed
    proc_file = PROCESSED_DIR / "weather_processed.csv"
    df.to_csv(proc_file, index=False)
    logger.info(f"Updated {proc_file} with authentic GHI data ({len(df)} records)")
    
    print(f"Dataset summary:")
    print(f"- Total records: {len(df)}")
    print(f"- Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"- Mean GHI (all hours): {df['solar_irradiance'].mean():.2f} W/m²")
    day_df = df[df['is_daylight'] == 1]
    print(f"- Mean GHI (daylight hours): {day_df['solar_irradiance'].mean():.2f} W/m²")
    print(f"- Max GHI: {df['solar_irradiance'].max():.2f} W/m²")
    print(f"- Max Rooftop PV Generation: {df['solar_generation_kw'].max():.2f} kW")

if __name__ == "__main__":
    fetch_and_process_historical_solar()
