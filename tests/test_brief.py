import json
from src import brief

RAW = {"stocks": {"ok": True, "groups": {}}, "fx": {"ok": True, "rates": []},
       "weather": {"ok": True, "locations": []}, "news": {"ok": True,
       "naver_economy": [], "global_semi": []}}


def test_generate_parses_claude_json(monkeypatch):
    payload = {"sections": {"markets": "M", "memory": "Mem",
               "weather": "W", "news": "N"}, "summary": "요약"}
    monkeypatch.setattr(brief, "_call_claude", lambda p: json.dumps(payload))
    out = brief.generate(RAW)
    assert out["summary"] == "요약"
    assert out["sections"]["markets"] == "M"
    assert out.get("degraded") is not True


def test_generate_fallback_on_error(monkeypatch):
    def boom(p):
        raise RuntimeError("rate limit")
    monkeypatch.setattr(brief, "_call_claude", boom)
    out = brief.generate(RAW)
    assert out["degraded"] is True
    assert out["sections"]["markets"] == ""
    assert "실패" in out["summary"]


def test_generate_fallback_on_bad_json(monkeypatch):
    monkeypatch.setattr(brief, "_call_claude", lambda p: "not json")
    out = brief.generate(RAW)
    assert out["degraded"] is True
