from src import render

RAW = {"stocks": {"ok": True, "groups": {"us_index": [
    {"symbol": "^GSPC", "name": "S&P 500", "price": 5000.0, "change_pct": -1.2}]}},
    "fx": {"ok": True, "rates": []},
    "weather": {"ok": True, "locations": [
        {"name": "남양주시", "hourly": [{"time": "07:00", "temp": 20.0,
         "precip_prob": 10, "code": 1}]}]},
    "news": {"ok": True, "naver_economy": [
        {"title": "경제뉴스", "link": "http://n"}],
        "market_news": [{"title": "코스피뉴스", "link": "http://m"}],
        "global_semi": []}}
BRIEF = {"sections": {"markets": "시장해석", "memory": "메모리분석",
         "weather": "날씨요약", "news": "뉴스요약"}, "summary": "핵심요약"}


def test_render_web_includes_sections():
    out = render.render_web(RAW, BRIEF, "2026-06-19 07:00 KST")
    assert "시장해석" in out
    assert "남양주시" in out
    assert "07:00" in out
    assert "경제뉴스" in out


def test_render_email_has_summary_link_and_sections():
    out = render.render_email(BRIEF, RAW, "https://x.github.io/daily-briefing/", "2026-06-19 07:00 KST")
    assert "핵심요약" in out
    assert "https://x.github.io/daily-briefing/" in out
    # 이메일에 섹션 분석도 포함(체계적 구성)
    assert "메모리분석" in out
    assert "시장해석" in out
    # 주요 지표 스냅샷 (S&P 500 가격 5,000.00 포맷)
    assert "5,000.00" in out
    # 뉴스 헤드라인
    assert "경제뉴스" in out
