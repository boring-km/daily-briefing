from src.collectors import fx


def test_collect_rates(monkeypatch):
    monkeypatch.setattr(fx, "_quote", lambda sym: (1350.0, -0.2))
    out = fx.collect()
    assert out["ok"] is True
    usdkrw = next(r for r in out["rates"] if r["pair"] == "KRW=X")
    assert usdkrw["name"] == "USD/KRW"
    assert usdkrw["price"] == 1350.0
