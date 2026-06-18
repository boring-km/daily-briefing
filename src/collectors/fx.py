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
        rates = []
        for pair, name in config.SETTINGS["tickers"]["fx"].items():
            price, change_pct = _quote(pair)
            rates.append({"pair": pair, "name": name,
                          "price": price, "change_pct": change_pct})
        return {"ok": True, "rates": rates}
    except Exception as e:
        return {"ok": False, "error": str(e)}
