from src.collectors import news


def test_collect_combines_sources(monkeypatch):
    monkeypatch.setattr(news, "_naver",
                        lambda q, c: [{"title": "경제뉴스", "link": "http://n"}])
    monkeypatch.setattr(news, "_rss",
                        lambda url, c: [{"title": "chip news", "link": "http://g"}])
    out = news.collect()
    assert out["ok"] is True
    assert out["naver_economy"][0]["title"] == "경제뉴스"
    assert out["global_semi"][0]["title"] == "chip news"
    assert len(out["market_news"]) > 0


def test_collect_failure(monkeypatch):
    def boom(*a):
        raise RuntimeError("api 401")
    monkeypatch.setattr(news, "_naver", boom)
    out = news.collect()
    assert out["ok"] is False
    assert "api 401" in out["error"]
