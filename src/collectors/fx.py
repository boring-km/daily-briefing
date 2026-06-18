import yfinance as yf
from src import config


def _quote(symbol: str):
    t = yf.Ticker(symbol)
    # period="5d" + dropna: 최신 행 Close가 NaN인 경우(장중/휴장) 유효 종가만 사용
    closes = t.history(period="5d")["Close"].dropna()
    if len(closes) < 1:
        raise ValueError(f"no data for {symbol}")
    last = float(closes.iloc[-1])
    prev = float(closes.iloc[-2]) if len(closes) >= 2 else last
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
