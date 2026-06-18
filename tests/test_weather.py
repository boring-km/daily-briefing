from src.collectors import weather

FAKE = {
    "hourly": {
        "time": ["2026-06-19T00:00", "2026-06-19T01:00"],
        "temperature_2m": [21.0, 20.5],
        "precipitation_probability": [10, 20],
        "weather_code": [1, 2],
    }
}


def test_collect_two_locations_with_hourly(monkeypatch):
    monkeypatch.setattr(weather, "_fetch", lambda lat, lon: FAKE)
    out = weather.collect()
    assert out["ok"] is True
    assert [l["name"] for l in out["locations"]] == ["남양주시", "동탄"]
    first = out["locations"][0]["hourly"][0]
    assert first["time"] == "00:00"
    assert first["temp"] == 21.0
    assert first["precip_prob"] == 10
    assert first["code"] == 1


def test_collect_failure(monkeypatch):
    def boom(lat, lon):
        raise ConnectionError("timeout")
    monkeypatch.setattr(weather, "_fetch", boom)
    out = weather.collect()
    assert out["ok"] is False
    assert "timeout" in out["error"]
