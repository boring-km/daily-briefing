import os

SETTINGS = {
    "weather_locations": [
        {"name": "남양주시", "lat": 37.636, "lon": 127.216},
        {"name": "동탄", "lat": 37.201, "lon": 127.073},
    ],
    "tickers": {
        "us_index": {"^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^SOX": "SOX"},
        "semis": {"NVDA": "NVIDIA", "AMD": "AMD", "MU": "Micron", "TSM": "TSMC"},
        "kr_memory": {"005930.KS": "삼성전자", "000660.KS": "SK하이닉스"},
        "fx": {"KRW=X": "USD/KRW", "EURKRW=X": "EUR/KRW", "JPYKRW=X": "JPY/KRW"},
    },
    "model": "sonnet",
    "pages_base_url": os.environ.get("PAGES_BASE_URL", "http://localhost"),
    "recipients": [e.strip() for e in
                   os.environ.get("BRIEF_RECIPIENT", "").split(",") if e.strip()],
}


def get_secret(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required secret: {name}")
    return val
