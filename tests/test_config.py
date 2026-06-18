import os
import pytest
from src import config


def test_settings_has_two_weather_locations():
    locs = config.SETTINGS["weather_locations"]
    assert [l["name"] for l in locs] == ["남양주시", "동탄"]
    assert all("lat" in l and "lon" in l for l in locs)


def test_settings_model_is_sonnet():
    assert config.SETTINGS["model"] == "sonnet"


def test_get_secret_reads_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert config.get_secret("ANTHROPIC_API_KEY") == "sk-test"


def test_get_secret_missing_raises(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(RuntimeError):
        config.get_secret("MISSING_KEY")


def test_recipients_parsed_as_list(monkeypatch):
    import importlib
    monkeypatch.setenv("BRIEF_RECIPIENT", "a@x.com, b@y.com ,c@z.com")
    importlib.reload(config)
    assert config.SETTINGS["recipients"] == ["a@x.com", "b@y.com", "c@z.com"]
