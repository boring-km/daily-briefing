import yfinance as yf
from src import config


def _quote(symbol: str):
    t = yf.Ticker(symbol)
    # period="5d" + dropna: 오늘/휴장일 행은 Close가 NaN이라 유효 종가만 추림
    # (한국장 005930.KS 등은 장중/지연 시 최신 행이 NaN).
    closes = t.history(period="5d")["Close"].dropna()
    if len(closes) < 1:
        raise ValueError(f"no data for {symbol}")
    last = float(closes.iloc[-1])
    prev = float(closes.iloc[-2]) if len(closes) >= 2 else last
    change_pct = ((last - prev) / prev * 100) if prev else 0.0
    return round(last, 2), round(change_pct, 2)


def collect() -> dict:
    try:
        tickers = config.SETTINGS["tickers"]
        groups = {}
        for group in [g for g in tickers if g != "fx"]:
            items = []
            for symbol, name in tickers[group].items():
                price, change_pct = _quote(symbol)
                items.append({"symbol": symbol, "name": name,
                              "price": price, "change_pct": change_pct})
            groups[group] = items
        return {"ok": True, "groups": groups}
    except Exception as e:
        return {"ok": False, "error": str(e)}
