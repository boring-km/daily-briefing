import requests
from src import config

_URL = "https://api.open-meteo.com/v1/forecast"


def _fetch(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": 1, "timezone": "Asia/Seoul",
    }
    r = requests.get(_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def collect() -> dict:
    try:
        locations = []
        for loc in config.SETTINGS["weather_locations"]:
            raw = _fetch(loc["lat"], loc["lon"])
            h = raw["hourly"]
            hourly = [
                {"time": t[-5:], "temp": temp, "precip_prob": pp, "code": code}
                for t, temp, pp, code in zip(
                    h["time"], h["temperature_2m"],
                    h["precipitation_probability"], h["weather_code"])
            ]
            locations.append({"name": loc["name"], "hourly": hourly})
        return {"ok": True, "locations": locations}
    except Exception as e:
        return {"ok": False, "error": str(e)}
