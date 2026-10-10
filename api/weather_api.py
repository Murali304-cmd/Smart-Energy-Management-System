import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests
from config.settings import OPENWEATHER_API_KEY, WEATHER_LAT, WEATHER_LON, WEATHER_API_BASE_URL
logger = logging.getLogger('SEMS.WeatherAPI')

def get_current_weather(lat: Optional[float]=None, lon: Optional[float]=None, api_key: Optional[str]=None, allow_demo_fallback: bool=False) -> Dict[str, Any]:
    target_lat = lat if lat is not None else WEATHER_LAT
    target_lon = lon if lon is not None else WEATHER_LON
    target_key = (api_key if api_key is not None else OPENWEATHER_API_KEY).strip()
    if not target_key or target_key == 'your_openweather_api_key_here':
        if allow_demo_fallback:
            return get_mock_weather(target_lat, target_lon)
        return {'status': 'error', 'source': 'OpenWeatherMap', 'message': 'Weather API unavailable: Missing OPENWEATHER_API_KEY'}
    params = {'lat': target_lat, 'lon': target_lon, 'appid': target_key, 'units': 'metric'}
    try:
        response = requests.get(WEATHER_API_BASE_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            dt_raw = data.get('dt')
            timestamp = datetime.fromtimestamp(dt_raw, tz=timezone.utc).isoformat() if dt_raw else datetime.now(timezone.utc).isoformat()
            main = data.get('main', {})
            weather_arr = data.get('weather', [{}])
            wind = data.get('wind', {})
            clouds = data.get('clouds', {})
            coord = data.get('coord', {})
            return {'status': 'success', 'timestamp': timestamp, 'temperature': float(main.get('temp', 0.0)), 'humidity': float(main.get('humidity', 0.0)), 'cloud_cover': float(clouds.get('all', 0.0)), 'wind_speed': float(wind.get('speed', 0.0)), 'weather_condition': str(weather_arr[0].get('main', 'Unknown')), 'latitude': float(coord.get('lat', target_lat)), 'longitude': float(coord.get('lon', target_lon)), 'data_type': 'live', 'source': 'OpenWeatherMap'}
        else:
            if allow_demo_fallback:
                return get_mock_weather(target_lat, target_lon)
            return {'status': 'error', 'source': 'OpenWeatherMap', 'message': f'Weather API unavailable (HTTP {response.status_code})'}
    except Exception as e:
        logger.error(f'Weather API error: {e}')
        if allow_demo_fallback:
            return get_mock_weather(target_lat, target_lon)
        return {'status': 'error', 'source': 'OpenWeatherMap', 'message': f'Weather API error: {str(e)}'}

def get_mock_weather(lat: float, lon: float) -> Dict[str, Any]:
    return {'status': 'success', 'timestamp': datetime.now(timezone.utc).isoformat(), 'temperature': 31.5, 'humidity': 68.0, 'cloud_cover': 20.0, 'wind_speed': 4.2, 'weather_condition': 'Clouds', 'latitude': lat, 'longitude': lon, 'data_type': 'demo', 'source': 'OpenWeatherMap-Demo'}
