import html
import requests
import feedparser
from src import config

_NAVER_URL = "https://openapi.naver.com/v1/search/news.json"
_GOOGLE_SEMI_RSS = ("https://news.google.com/rss/search"
                    "?q=semiconductor&hl=en-US&gl=US&ceid=US:en")


def _strip(text: str) -> str:
    import re
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _naver(query: str, count: int) -> list:
    headers = {
        "X-Naver-Client-Id": config.get_secret("NAVER_CLIENT_ID"),
        "X-Naver-Client-Secret": config.get_secret("NAVER_CLIENT_SECRET"),
    }
    params = {"query": query, "display": count, "sort": "date"}
    r = requests.get(_NAVER_URL, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return [{"title": _strip(it["title"]), "link": it["link"]}
            for it in r.json().get("items", [])]


def _rss(url: str, count: int) -> list:
    feed = feedparser.parse(url)
    return [{"title": e.title, "link": e.link} for e in feed.entries[:count]]


def collect() -> dict:
    try:
        return {
            "ok": True,
            "naver_economy": _naver("경제", 6),
            "global_semi": _rss(_GOOGLE_SEMI_RSS, 6),
            "market_news": _naver("코스피", 4) + _naver("나스닥", 4),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
