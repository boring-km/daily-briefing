import yfinance as yf
from src import config


def _quote(symbol: str):
    t = yf.Ticker(symbol)
    hist = t.history(period="2d")
    if len(hist) < 1:
        raise ValueError(f"no data for {symbol}")
    last = float(hist["Close"].iloc[-1])
    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else last
    change_pct = ((last - prev) / prev * 100) if prev else 0.0
    return round(last, 2), round(change_pct, 2)


def collect() -> dict:
    try:
        tickers = config.SETTINGS["tickers"]
        groups = {}
        for group in ("us_index", "semis", "kr_memory"):
            items = []
            for symbol, name in tickers[group].items():
                price, change_pct = _quote(symbol)
                items.append({"symbol": symbol, "name": name,
                              "price": price, "change_pct": change_pct})
            groups[group] = items
        return {"ok": True, "groups": groups}
    except Exception as e:
        return {"ok": False, "error": str(e)}
