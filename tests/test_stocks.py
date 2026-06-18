from src.collectors import stocks


def test_collect_groups_present(monkeypatch):
    monkeypatch.setattr(stocks, "_quote", lambda sym: (100.0, 1.5))
    out = stocks.collect()
    assert out["ok"] is True
    assert set(out["groups"]) == {"us_index", "semis", "kr_memory", "us_m7"}
    nvda = next(i for i in out["groups"]["semis"] if i["symbol"] == "NVDA")
    assert nvda["name"] == "NVIDIA"
    assert nvda["change_pct"] == 1.5
    aapl = next(i for i in out["groups"]["us_m7"] if i["symbol"] == "AAPL")
    assert aapl["name"] == "Apple"
    assert aapl["change_pct"] == 1.5


def test_collect_handles_failure(monkeypatch):
    def boom(sym):
        raise ValueError("network down")
    monkeypatch.setattr(stocks, "_quote", boom)
    out = stocks.collect()
    assert out["ok"] is False
    assert "network down" in out["error"]
