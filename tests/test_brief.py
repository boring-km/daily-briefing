from src import brief

RAW = {"stocks": {"ok": True, "groups": {}}, "fx": {"ok": True, "rates": []},
       "weather": {"ok": True, "locations": []}, "news": {"ok": True,
       "naver_economy": [], "global_semi": []}}

_MARKER_OUT = """군더더기 무시됨
===MARKETS===
• 시장 불릿1
• 시장 불릿2
===MEMORY===
• 메모리 분석
===WEATHER===
날씨 요약 문장.
===NEWS===
• 뉴스 핵심
===SUMMARY===
핵심 요약 문장.
===END===
"""


def test_generate_parses_marker_format(monkeypatch):
    monkeypatch.setattr(brief, "_call_claude", lambda p: _MARKER_OUT)
    out = brief.generate(RAW)
    assert out["summary"] == "핵심 요약 문장."
    assert out["sections"]["markets"] == "• 시장 불릿1\n• 시장 불릿2"
    assert out["sections"]["weather"] == "날씨 요약 문장."
    assert out.get("degraded") is not True


def test_generate_handles_unescaped_quotes_and_newlines(monkeypatch):
    # 마커 포맷은 따옴표/줄바꿈을 그대로 담아도 깨지지 않음 (JSON 문제 해결 확인)
    tricky = ('===MARKETS===\n• 그는 "강세장"이라 말함\n• 다음 줄\n'
              '===MEMORY===\nm\n===WEATHER===\nw\n===NEWS===\nn\n'
              '===SUMMARY===\n"인용" 포함 요약\n===END===')
    monkeypatch.setattr(brief, "_call_claude", lambda p: tricky)
    out = brief.generate(RAW)
    assert out.get("degraded") is not True
    assert '"강세장"' in out["sections"]["markets"]
    assert '"인용" 포함 요약' == out["summary"]


def test_generate_fallback_on_error(monkeypatch):
    def boom(p):
        raise RuntimeError("rate limit")
    monkeypatch.setattr(brief, "_call_claude", boom)
    out = brief.generate(RAW)
    assert out["degraded"] is True
    assert out["sections"]["markets"] == ""
    assert "실패" in out["summary"]


def test_generate_fallback_on_unparseable(monkeypatch):
    # 마커 하나도 없는 출력 → 파싱 실패 → 폴백
    monkeypatch.setattr(brief, "_call_claude", lambda p: "그냥 잡담, 마커 없음")
    out = brief.generate(RAW)
    assert out["degraded"] is True
