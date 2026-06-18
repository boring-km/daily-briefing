# Daily Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매일 3회 데이터를 수집해 Claude로 해석·요약하고, 웹(GitHub Pages)에 배포하면서 요약을 이메일(Gmail SMTP)로 발송하는 AI 데일리 브리핑 자동화.

**Architecture:** 독립적인 collector들이 외부 소스에서 정규화된 dict를 만들고, `brief.py`가 로컬 Claude Code CLI(`claude -p`)로 섹션 해석 + 이메일 요약을 생성, `render.py`가 웹/이메일 HTML로 렌더, `main.py`가 오케스트레이션하며 git push(웹 배포)와 SMTP 발송을 수행. macOS launchd가 이 PC에서 하루 3회 트리거.

**Tech Stack:** Python 3.11, yfinance, requests, feedparser, jinja2, **Claude Code CLI (`claude -p`)**, pytest, macOS launchd, GitHub Pages.

## Global Constraints

- Python 3.11+. 의존성은 `requirements.txt`에 고정(`==` 버전).
- 모든 collector 인터페이스: 모듈 함수 `collect(...) -> dict`, 네트워크/파싱만 담당, 해석 텍스트 생성 금지.
- 외부 호출 실패는 예외를 던지지 말고 `{"ok": False, "error": str}` 형태로 반환(섹션 격리).
- 시크릿은 환경변수에서만 읽음: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`. 코드/레포에 하드코딩 금지. (ANTHROPIC_API_KEY 불필요 — Claude Code CLI 구독 사용)
- 날씨 지역 2곳: 남양주시(`lat=37.636, lon=127.216`), 동탄(`lat=37.201, lon=127.073`). 시간대별 1시간 단위.
- 시간대: 출력·파일명·스케줄 모두 KST(Asia/Seoul) 기준.
- LLM: 로컬 `claude -p --model sonnet` (subprocess). API 키 없음.
- Pages URL 형식: `https://<GH_USER>.github.io/<REPO>/` (이메일 링크는 환경변수 `PAGES_BASE_URL`로 주입).
- TDD: 각 태스크는 실패 테스트 → 구현 → 통과 → 커밋 순서. 네트워크는 mock.

---

### Task 1: 프로젝트 스캐폴딩 & 설정

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/collectors/__init__.py`
- Create: `src/config.py`
- Create: `tests/__init__.py`
- Test: `tests/test_config.py`
- Create: `pytest.ini`

**Interfaces:**
- Consumes: 없음
- Produces: `config.SETTINGS` (dict) — 키: `weather_locations` (list of `{name, lat, lon}`), `tickers` (dict), `model` (str), `pages_base_url` (str), `recipients` (list[str], `BRIEF_RECIPIENT` 콤마 분리). `config.get_secret(name: str) -> str` (없으면 `RuntimeError`).

- [ ] **Step 1: requirements.txt 작성**

```
yfinance==0.2.66
requests==2.32.5
feedparser==6.0.11
jinja2==3.1.6
pytest==8.4.2
```

> Claude는 SDK 대신 로컬 `claude` CLI를 subprocess로 호출하므로 anthropic 패키지 불필요.

- [ ] **Step 2: pytest.ini 작성**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 3: 빈 패키지 파일 생성**

`src/__init__.py`, `src/collectors/__init__.py`, `tests/__init__.py` — 빈 파일.

- [ ] **Step 4: 실패 테스트 작성** — `tests/test_config.py`

```python
import os
import pytest
from src import config


def test_settings_has_two_weather_locations():
    locs = config.SETTINGS["weather_locations"]
    assert [l["name"] for l in locs] == ["남양주시", "동탄"]
    assert all("lat" in l and "lon" in l for l in locs)


def test_settings_model_is_sonnet():
    assert config.SETTINGS["model"] == "sonnet"


def test_get_secret_reads_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert config.get_secret("ANTHROPIC_API_KEY") == "sk-test"


def test_get_secret_missing_raises(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(RuntimeError):
        config.get_secret("MISSING_KEY")


def test_recipients_parsed_as_list(monkeypatch):
    import importlib
    monkeypatch.setenv("BRIEF_RECIPIENT", "a@x.com, b@y.com ,c@z.com")
    importlib.reload(config)
    assert config.SETTINGS["recipients"] == ["a@x.com", "b@y.com", "c@z.com"]
```

- [ ] **Step 5: 테스트 실패 확인**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 6: config.py 구현**

```python
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
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `pytest tests/test_config.py -v`
Expected: PASS (4 passed)

- [ ] **Step 8: 커밋**

```bash
git add requirements.txt pytest.ini src/ tests/
git commit -m "feat: project scaffolding and config"
```

---

### Task 2: 증시·환율 collector (stocks, fx)

**Files:**
- Create: `src/collectors/stocks.py`
- Create: `src/collectors/fx.py`
- Test: `tests/test_stocks.py`
- Test: `tests/test_fx.py`

**Interfaces:**
- Consumes: `config.SETTINGS["tickers"]`
- Produces:
  - `stocks.collect() -> dict` → `{"ok": True, "groups": {"us_index": [...], "semis": [...], "kr_memory": [...]}}` where each item is `{"symbol", "name", "price": float, "change_pct": float}`. 실패 시 `{"ok": False, "error": str}`.
  - `fx.collect() -> dict` → `{"ok": True, "rates": [{"pair", "name", "price", "change_pct"}]}` 또는 `{"ok": False, "error": str}`.
  - 둘 다 내부적으로 `_quote(symbol) -> (price, change_pct)` 헬퍼를 yfinance로 구현. 테스트는 yfinance를 monkeypatch.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_stocks.py`

```python
from src.collectors import stocks


def test_collect_groups_present(monkeypatch):
    monkeypatch.setattr(stocks, "_quote", lambda sym: (100.0, 1.5))
    out = stocks.collect()
    assert out["ok"] is True
    assert set(out["groups"]) == {"us_index", "semis", "kr_memory"}
    nvda = next(i for i in out["groups"]["semis"] if i["symbol"] == "NVDA")
    assert nvda["name"] == "NVIDIA"
    assert nvda["change_pct"] == 1.5


def test_collect_handles_failure(monkeypatch):
    def boom(sym):
        raise ValueError("network down")
    monkeypatch.setattr(stocks, "_quote", boom)
    out = stocks.collect()
    assert out["ok"] is False
    assert "network down" in out["error"]
```

- [ ] **Step 2: 실패 테스트 작성** — `tests/test_fx.py`

```python
from src.collectors import fx


def test_collect_rates(monkeypatch):
    monkeypatch.setattr(fx, "_quote", lambda sym: (1350.0, -0.2))
    out = fx.collect()
    assert out["ok"] is True
    usdkrw = next(r for r in out["rates"] if r["pair"] == "KRW=X")
    assert usdkrw["name"] == "USD/KRW"
    assert usdkrw["price"] == 1350.0
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `pytest tests/test_stocks.py tests/test_fx.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: stocks.py 구현**

```python
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
```

- [ ] **Step 5: fx.py 구현**

```python
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
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `pytest tests/test_stocks.py tests/test_fx.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: 커밋**

```bash
git add src/collectors/stocks.py src/collectors/fx.py tests/test_stocks.py tests/test_fx.py
git commit -m "feat: stocks and fx collectors"
```

---

### Task 3: 날씨 collector (Open-Meteo, 시간대별)

**Files:**
- Create: `src/collectors/weather.py`
- Test: `tests/test_weather.py`

**Interfaces:**
- Consumes: `config.SETTINGS["weather_locations"]`, `requests`
- Produces: `weather.collect() -> dict` →
  `{"ok": True, "locations": [{"name": str, "hourly": [{"time": "HH:MM", "temp": float, "precip_prob": int, "code": int}]}]}`.
  내부 `_fetch(lat, lon) -> dict` (raw JSON 반환)을 requests로 구현, 테스트에서 monkeypatch.
  Open-Meteo 엔드포인트: `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&hourly=temperature_2m,precipitation_probability,weather_code&forecast_days=1&timezone=Asia%2FSeoul`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_weather.py`

```python
from src.collectors import weather

FAKE = {
    "hourly": {
        "time": ["2026-06-19T00:00", "2026-06-19T01:00"],
        "temperature_2m": [21.0, 20.5],
        "precipitation_probability": [10, 20],
        "weather_code": [1, 2],
    }
}


def test_collect_two_locations_with_hourly(monkeypatch):
    monkeypatch.setattr(weather, "_fetch", lambda lat, lon: FAKE)
    out = weather.collect()
    assert out["ok"] is True
    assert [l["name"] for l in out["locations"]] == ["남양주시", "동탄"]
    first = out["locations"][0]["hourly"][0]
    assert first["time"] == "00:00"
    assert first["temp"] == 21.0
    assert first["precip_prob"] == 10
    assert first["code"] == 1


def test_collect_failure(monkeypatch):
    def boom(lat, lon):
        raise ConnectionError("timeout")
    monkeypatch.setattr(weather, "_fetch", boom)
    out = weather.collect()
    assert out["ok"] is False
    assert "timeout" in out["error"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_weather.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: weather.py 구현**

```python
import requests
from src import config

_URL = "https://api.open-meteo.com/v1/forecast"


def _fetch(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": 1, "timezone": "Asia/Seoul",
    }
    r = requests.get(_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def collect() -> dict:
    try:
        locations = []
        for loc in config.SETTINGS["weather_locations"]:
            raw = _fetch(loc["lat"], loc["lon"])
            h = raw["hourly"]
            hourly = [
                {"time": t[-5:], "temp": temp, "precip_prob": pp, "code": code}
                for t, temp, pp, code in zip(
                    h["time"], h["temperature_2m"],
                    h["precipitation_probability"], h["weather_code"])
            ]
            locations.append({"name": loc["name"], "hourly": hourly})
        return {"ok": True, "locations": locations}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_weather.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/collectors/weather.py tests/test_weather.py
git commit -m "feat: weather collector with hourly forecast"
```

---

### Task 4: 뉴스 collector (네이버 경제 + Google News RSS)

**Files:**
- Create: `src/collectors/news.py`
- Test: `tests/test_news.py`

**Interfaces:**
- Consumes: `config.get_secret("NAVER_CLIENT_ID"/"NAVER_CLIENT_SECRET")`, `requests`, `feedparser`
- Produces: `news.collect() -> dict` →
  `{"ok": True, "naver_economy": [{"title", "link"}], "global_semi": [{"title", "link"}]}`.
  내부 헬퍼: `_naver(query: str, count: int) -> list[dict]` (requests, 네이버 검색 API), `_rss(url: str, count: int) -> list[dict]` (feedparser). 둘 다 테스트에서 monkeypatch.
  네이버 엔드포인트: `https://openapi.naver.com/v1/search/news.json?query=경제&display=5&sort=date`, 헤더 `X-Naver-Client-Id`, `X-Naver-Client-Secret`.
  Google News RSS: `https://news.google.com/rss/search?q=semiconductor&hl=en-US&gl=US&ceid=US:en`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_news.py`

```python
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


def test_collect_failure(monkeypatch):
    def boom(*a):
        raise RuntimeError("api 401")
    monkeypatch.setattr(news, "_naver", boom)
    out = news.collect()
    assert out["ok"] is False
    assert "api 401" in out["error"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_news.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: news.py 구현**

```python
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
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_news.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/collectors/news.py tests/test_news.py
git commit -m "feat: news collector (naver economy + google rss)"
```

---

### Task 5: Claude 브리핑 생성 (brief.py)

**Files:**
- Create: `src/brief.py`
- Test: `tests/test_brief.py`

**Interfaces:**
- Consumes: 모든 collector 출력 dict, 로컬 `claude` CLI(subprocess), `config`
- Produces: `brief.generate(raw: dict) -> dict` →
  `{"sections": {"markets": str, "memory": str, "weather": str, "news": str}, "summary": str}`.
  `raw`는 `{"stocks":..., "fx":..., "weather":..., "news":...}`. 내부 `_call_claude(prompt: str) -> str`를 **`subprocess.run(["claude", "-p", "--model", "sonnet", prompt])`** 로 구현(테스트에서 monkeypatch). Claude 실패/타임아웃 시 폴백: 각 섹션 `""`, summary는 `"(요약 생성 실패 — 수치만 표시)"`, 반환 dict에 `"degraded": True`.
  Claude에 JSON 출력을 요청하고 파싱; 파싱 실패도 폴백 처리.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_brief.py`

```python
import json
from src import brief

RAW = {"stocks": {"ok": True, "groups": {}}, "fx": {"ok": True, "rates": []},
       "weather": {"ok": True, "locations": []}, "news": {"ok": True,
       "naver_economy": [], "global_semi": []}}


def test_generate_parses_claude_json(monkeypatch):
    payload = {"sections": {"markets": "M", "memory": "Mem",
               "weather": "W", "news": "N"}, "summary": "요약"}
    monkeypatch.setattr(brief, "_call_claude", lambda p: json.dumps(payload))
    out = brief.generate(RAW)
    assert out["summary"] == "요약"
    assert out["sections"]["markets"] == "M"
    assert out.get("degraded") is not True


def test_generate_fallback_on_error(monkeypatch):
    def boom(p):
        raise RuntimeError("rate limit")
    monkeypatch.setattr(brief, "_call_claude", boom)
    out = brief.generate(RAW)
    assert out["degraded"] is True
    assert out["sections"]["markets"] == ""
    assert "실패" in out["summary"]


def test_generate_fallback_on_bad_json(monkeypatch):
    monkeypatch.setattr(brief, "_call_claude", lambda p: "not json")
    out = brief.generate(RAW)
    assert out["degraded"] is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_brief.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: brief.py 구현**

```python
import json
import subprocess
from src import config

_SECTIONS = ("markets", "memory", "weather", "news")

_PROMPT = """당신은 한국어 데일리 브리핑 애널리스트입니다.
아래 JSON 데이터를 바탕으로 투자/생활 관점의 간결한 해석을 작성하세요.
반드시 아래 형식의 JSON만 출력하세요(설명 금지):
{{"sections": {{"markets": "...", "memory": "...", "weather": "...", "news": "..."}}, "summary": "..."}}
- markets: 미국증시/반도체/한국메모리/환율 종합 해석 (3~5문장)
- memory: HBM/DRAM/NAND 메모리 섹터 분석 (2~4문장)
- weather: 남양주·동탄 시간대별 날씨 요약 및 생활 팁 (2~3문장)
- news: 경제·반도체 뉴스 핵심 (3~4문장)
- summary: 이메일용 전체 핵심 요약 (3~4문장, 가장 중요한 것만)

데이터:
{data}
"""


def _call_claude(prompt: str) -> str:
    # 로컬 Claude Code CLI 헤드리스 호출 (로그인된 구독 사용, API 키 불필요)
    result = subprocess.run(
        ["claude", "-p", "--model", config.SETTINGS["model"], prompt],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr.strip()}")
    return result.stdout


def _fallback() -> dict:
    return {"sections": {s: "" for s in _SECTIONS},
            "summary": "(요약 생성 실패 — 수치만 표시)", "degraded": True}


def generate(raw: dict) -> dict:
    try:
        prompt = _PROMPT.format(data=json.dumps(raw, ensure_ascii=False))
        text = _call_claude(prompt)
        start, end = text.find("{"), text.rfind("}")
        parsed = json.loads(text[start:end + 1])
        if "sections" not in parsed or "summary" not in parsed:
            return _fallback()
        for s in _SECTIONS:
            parsed["sections"].setdefault(s, "")
        return parsed
    except Exception:
        return _fallback()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_brief.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/brief.py tests/test_brief.py
git commit -m "feat: claude briefing generation with fallback"
```

---

### Task 6: 렌더링 (render.py + 임시 템플릿)

**Files:**
- Create: `src/render.py`
- Create: `templates/web.html.j2`
- Create: `templates/email.html.j2`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `raw` dict, `brief.generate` 출력 dict, `jinja2`
- Produces:
  - `render.render_web(raw: dict, brief: dict, generated_at: str) -> str` (전체 상세 HTML)
  - `render.render_email(brief: dict, web_url: str, generated_at: str) -> str` (요약 + 링크 HTML)
  - 둘 다 jinja2 `Environment(loader=FileSystemLoader("templates"))` 사용.
- 이 태스크의 템플릿은 **기능 동작용 최소 버전**. 시각 디자인은 Task 9(impeccable)에서 교체.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_render.py`

```python
from src import render

RAW = {"stocks": {"ok": True, "groups": {"us_index": [
    {"symbol": "^GSPC", "name": "S&P 500", "price": 5000.0, "change_pct": -1.2}]}},
    "fx": {"ok": True, "rates": []},
    "weather": {"ok": True, "locations": [
        {"name": "남양주시", "hourly": [{"time": "07:00", "temp": 20.0,
         "precip_prob": 10, "code": 1}]}]},
    "news": {"ok": True, "naver_economy": [
        {"title": "경제뉴스", "link": "http://n"}], "global_semi": []}}
BRIEF = {"sections": {"markets": "시장해석", "memory": "메모리분석",
         "weather": "날씨요약", "news": "뉴스요약"}, "summary": "핵심요약"}


def test_render_web_includes_sections():
    out = render.render_web(RAW, BRIEF, "2026-06-19 07:00 KST")
    assert "시장해석" in out
    assert "남양주시" in out
    assert "07:00" in out
    assert "경제뉴스" in out


def test_render_email_has_summary_and_link():
    out = render.render_email(BRIEF, "https://x.github.io/daily-briefing/", "2026-06-19 07:00 KST")
    assert "핵심요약" in out
    assert "https://x.github.io/daily-briefing/" in out
    # 이메일은 요약만 — 전체 섹션 본문은 넣지 않음
    assert "메모리분석" not in out
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 템플릿 작성** — `templates/web.html.j2`

```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>AI 데일리 브리핑 — {{ generated_at }}</title></head>
<body>
<h1>AI 데일리 브리핑</h1>
<p>{{ generated_at }}</p>

<section><h2>시장</h2><p>{{ brief.sections.markets }}</p>
{% for group, items in raw.stocks.groups.items() if raw.stocks.ok %}
<h3>{{ group }}</h3><ul>
{% for it in items %}<li>{{ it.name }}: {{ it.price }} ({{ it.change_pct }}%)</li>{% endfor %}
</ul>{% endfor %}</section>

<section><h2>메모리</h2><p>{{ brief.sections.memory }}</p></section>

<section><h2>날씨</h2><p>{{ brief.sections.weather }}</p>
{% for loc in raw.weather.locations if raw.weather.ok %}
<h3>{{ loc.name }}</h3><ul>
{% for h in loc.hourly %}<li>{{ h.time }} — {{ h.temp }}°C, 강수 {{ h.precip_prob }}%</li>{% endfor %}
</ul>{% endfor %}</section>

<section><h2>뉴스</h2><p>{{ brief.sections.news }}</p>
<ul>{% for n in raw.news.naver_economy if raw.news.ok %}
<li><a href="{{ n.link }}">{{ n.title }}</a></li>{% endfor %}</ul></section>
</body></html>
```

- [ ] **Step 4: 최소 템플릿 작성** — `templates/email.html.j2`

```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"></head>
<body>
<h1>AI 데일리 브리핑 요약</h1>
<p>{{ generated_at }}</p>
<p>{{ brief.summary }}</p>
<p><a href="{{ web_url }}">웹에서 자세히 보기 →</a></p>
</body></html>
```

- [ ] **Step 5: render.py 구현**

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "j2"]),
)


def render_web(raw: dict, brief: dict, generated_at: str) -> str:
    return _env.get_template("web.html.j2").render(
        raw=raw, brief=brief, generated_at=generated_at)


def render_email(brief: dict, web_url: str, generated_at: str) -> str:
    return _env.get_template("email.html.j2").render(
        brief=brief, web_url=web_url, generated_at=generated_at)
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `pytest tests/test_render.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add src/render.py templates/ tests/test_render.py
git commit -m "feat: web and email rendering (minimal templates)"
```

---

### Task 7: 이메일 발송 (mailer.py)

**Files:**
- Create: `src/mailer.py`
- Test: `tests/test_mailer.py`

**Interfaces:**
- Consumes: `config.get_secret`, `smtplib`, `email.message`
- Produces: `mailer.send(html: str, subject: str, recipients: list[str]) -> bool`.
  `msg["To"]`는 `", ".join(recipients)`. 빈 리스트면 발송 생략하고 `False`. 내부 `_smtp_send(msg)`를 `smtplib.SMTP_SSL("smtp.gmail.com", 465)`로 구현(테스트에서 monkeypatch). 발송 실패 시 1회 재시도 후 실패면 `False` 반환.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_mailer.py`

```python
from src import mailer


def test_send_success_multiple_recipients(monkeypatch):
    sent = {}
    def fake_send(msg):
        sent["to"] = msg["To"]
        sent["subject"] = msg["Subject"]
    monkeypatch.setenv("GMAIL_USER", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(mailer, "_smtp_send", fake_send)
    ok = mailer.send("<p>hi</p>", "제목", ["a@x.com", "b@y.com"])
    assert ok is True
    assert sent["to"] == "a@x.com, b@y.com"
    assert sent["subject"] == "제목"


def test_send_empty_recipients_returns_false(monkeypatch):
    monkeypatch.setattr(mailer, "_smtp_send",
                        lambda msg: (_ for _ in ()).throw(AssertionError("should not send")))
    assert mailer.send("<p>hi</p>", "제목", []) is False


def test_send_retries_then_fails(monkeypatch):
    calls = {"n": 0}
    def boom(msg):
        calls["n"] += 1
        raise OSError("smtp down")
    monkeypatch.setenv("GMAIL_USER", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(mailer, "_smtp_send", boom)
    ok = mailer.send("<p>hi</p>", "제목", ["you@gmail.com"])
    assert ok is False
    assert calls["n"] == 2  # 최초 + 재시도 1회
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_mailer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: mailer.py 구현**

```python
import smtplib
from email.message import EmailMessage
from src import config


def _smtp_send(msg: EmailMessage) -> None:
    user = config.get_secret("GMAIL_USER")
    pw = config.get_secret("GMAIL_APP_PASSWORD")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)


def send(html: str, subject: str, recipients: list) -> bool:
    if not recipients:
        return False
    msg = EmailMessage()
    msg["From"] = config.get_secret("GMAIL_USER")
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("HTML 메일입니다. HTML 지원 클라이언트로 보세요.")
    msg.add_alternative(html, subtype="html")
    for attempt in range(2):
        try:
            _smtp_send(msg)
            return True
        except Exception:
            if attempt == 1:
                return False
    return False
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_mailer.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/mailer.py tests/test_mailer.py
git commit -m "feat: gmail smtp mailer with retry"
```

---

### Task 8: 오케스트레이션 (main.py)

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: 모든 collector, `brief`, `render`, `mailer`, `config`
- Produces: `main.run(dry_run: bool = False) -> dict` →
  `{"web_path": str, "archive_path": str, "email_sent": bool}`.
  동작: collector 4개 호출 → `raw` 구성 → `brief.generate(raw)` → `render_web`/`render_email` →
  `docs/index.html` + `docs/archive/<KST YYYY-MM-DD-HHmm>.html` 기록 →
  `dry_run`이 아니면 `mailer.send` 호출. `dry_run`이면 파일만 쓰고 `email_sent=False`.
  KST 타임스탬프 헬퍼 `_now_kst() -> datetime` 분리(테스트에서 monkeypatch 가능). `__main__` 블록은 `--dry-run` 플래그 파싱.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_main.py`

```python
from datetime import datetime
from src import main


def test_run_dry_writes_files_no_email(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(main.stocks, "collect", lambda: {"ok": True, "groups": {}})
    monkeypatch.setattr(main.fx, "collect", lambda: {"ok": True, "rates": []})
    monkeypatch.setattr(main.weather, "collect", lambda: {"ok": True, "locations": []})
    monkeypatch.setattr(main.news, "collect",
                        lambda: {"ok": True, "naver_economy": [], "global_semi": []})
    monkeypatch.setattr(main.brief, "generate",
                        lambda raw: {"sections": {"markets": "", "memory": "",
                        "weather": "", "news": ""}, "summary": "요약"})
    sent = {"called": False}
    monkeypatch.setattr(main.mailer, "send",
                        lambda *a, **k: sent.__setitem__("called", True) or True)
    monkeypatch.setattr(main, "_now_kst", lambda: datetime(2026, 6, 19, 7, 0))

    out = main.run(dry_run=True)
    assert out["email_sent"] is False
    assert sent["called"] is False
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "archive" / "2026-06-19-0700.html").exists()


def test_run_sends_email(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DOCS_DIR", str(tmp_path))
    for mod in (main.stocks, main.fx, main.weather, main.news):
        pass
    monkeypatch.setattr(main.stocks, "collect", lambda: {"ok": True, "groups": {}})
    monkeypatch.setattr(main.fx, "collect", lambda: {"ok": True, "rates": []})
    monkeypatch.setattr(main.weather, "collect", lambda: {"ok": True, "locations": []})
    monkeypatch.setattr(main.news, "collect",
                        lambda: {"ok": True, "naver_economy": [], "global_semi": []})
    monkeypatch.setattr(main.brief, "generate",
                        lambda raw: {"sections": {"markets": "", "memory": "",
                        "weather": "", "news": ""}, "summary": "요약"})
    captured = {}
    monkeypatch.setattr(main.mailer, "send",
                        lambda html, subject, recipient: captured.update(
                            {"subject": subject, "to": recipient}) or True)
    monkeypatch.setattr(main, "_now_kst", lambda: datetime(2026, 6, 19, 19, 0))

    out = main.run(dry_run=False)
    assert out["email_sent"] is True
    assert "2026-06-19" in captured["subject"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: main.py 구현**

```python
import os
import sys
from datetime import datetime, timezone, timedelta

from src import config, brief, render, mailer
from src.collectors import stocks, fx, weather, news

DOCS_DIR = "docs"
_KST = timezone(timedelta(hours=9))


def _now_kst() -> datetime:
    return datetime.now(_KST)


def run(dry_run: bool = False) -> dict:
    raw = {
        "stocks": stocks.collect(),
        "fx": fx.collect(),
        "weather": weather.collect(),
        "news": news.collect(),
    }
    b = brief.generate(raw)

    now = _now_kst()
    generated_at = now.strftime("%Y-%m-%d %H:%M KST")
    stamp = now.strftime("%Y-%m-%d-%H%M")
    date_str = now.strftime("%Y-%m-%d")

    web_url = config.SETTINGS["pages_base_url"].rstrip("/") + "/"
    web_html = render.render_web(raw, b, generated_at)
    email_html = render.render_email(b, web_url, generated_at)

    os.makedirs(os.path.join(DOCS_DIR, "archive"), exist_ok=True)
    web_path = os.path.join(DOCS_DIR, "index.html")
    archive_path = os.path.join(DOCS_DIR, "archive", f"{stamp}.html")
    for p in (web_path, archive_path):
        with open(p, "w", encoding="utf-8") as f:
            f.write(web_html)

    email_sent = False
    if not dry_run:
        subject = f"[AI 브리핑] {date_str} {now.strftime('%H:%M')}"
        email_sent = mailer.send(email_html, subject, config.SETTINGS["recipients"])

    return {"web_path": web_path, "archive_path": archive_path,
            "email_sent": email_sent}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    result = run(dry_run=dry)
    print(result)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 테스트 통과 확인**

Run: `pytest -v`
Expected: PASS (전 태스크 테스트 모두 통과)

- [ ] **Step 6: 커밋**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: orchestration main with dry-run"
```

---

### Task 9: 웹 디자인 (impeccable)

**Files:**
- Modify: `templates/web.html.j2`
- Modify: `templates/email.html.j2`
- Test: `tests/test_render.py` (기존 테스트 계속 통과해야 함)

**Interfaces:**
- Consumes/Produces: Task 6과 동일 (render 함수 시그니처 불변). 템플릿 변수명(`raw`, `brief`, `generated_at`, `web_url`)은 절대 바꾸지 않음 — 디자인/마크업/CSS만 교체.

- [ ] **Step 1: impeccable 스킬 호출**

Run skill: `frontend-design:frontend-design` 또는 `impeccable` 스킬을 invoke하여 웹 대시보드 디자인.
요구사항을 스킬에 전달:
- AI 데일리 브리핑 대시보드, 한국어
- 섹션 카드: 시장(증시·환율 표), 메모리 분석, 날씨, 뉴스
- 날씨는 **남양주·동탄 시간대별 1시간 단위** 타임라인/차트 시각화
- 다크/라이트 무드, 한국어 타이포그래피, 모바일 반응형
- 단일 HTML(인라인 CSS, 외부 빌드 의존성 없음 — jinja2로 렌더되는 정적 파일)

- [ ] **Step 2: web.html.j2 디자인 적용**

impeccable 산출물을 jinja2 템플릿으로 이식. **기존 변수/루프 구조 유지**:
- `raw.stocks.groups`, `raw.fx.rates`, `raw.weather.locations[].hourly[]`, `raw.news.naver_economy`, `raw.news.global_semi`
- `brief.sections.{markets,memory,weather,news}`, `generated_at`
- `{% if raw.X.ok %}` 가드로 실패 섹션은 "데이터 없음" 표기

- [ ] **Step 3: email.html.j2 디자인 적용**

이메일 클라이언트 호환을 위해 **인라인 스타일 + 테이블 레이아웃**. 변수 유지: `brief.summary`, `web_url`, `generated_at`. 요약 + CTA 버튼(웹 링크)만 — 전체 섹션 본문 금지.

- [ ] **Step 4: 렌더 테스트 통과 확인**

Run: `pytest tests/test_render.py -v`
Expected: PASS (디자인 바뀌어도 필수 변수 출력 유지)

- [ ] **Step 5: 로컬 dry-run으로 육안 확인**

Run: `PAGES_BASE_URL=https://example.github.io/daily-briefing python -m src.main --dry-run`
브라우저로 `docs/index.html` 열어 디자인 확인.

- [ ] **Step 6: 커밋**

```bash
git add templates/ 
git commit -m "feat: impeccable web and email design"
```

---

### Task 10: 로컬 스케줄(launchd) + 배포 스크립트 & 문서

**Files:**
- Create: `run.sh`
- Create: `.env.example`
- Create: `com.daily-briefing.plist` (LaunchAgent 템플릿)
- Create: `README.md`

**Interfaces:**
- Consumes: `.env`(시크릿), `src.main`, 로컬 `claude` CLI, git remote
- Produces: launchd가 하루 3회 `run.sh` 실행 → 데이터 생성 → `docs/` 커밋·푸시(Pages 배포) → 이메일 발송.

- [ ] **Step 1: 배포 스크립트 작성** — `run.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# .env 로드 (GMAIL_*, NAVER_*, PAGES_BASE_URL, BRIEF_RECIPIENT)
set -a
[ -f .env ] && . ./.env
set +a

# 절전 방지하며 실행 (최대 10분)
caffeinate -i python3 -m src.main

# 웹 배포: docs 변경분 커밋·푸시 → GitHub Pages
git add docs/
git commit -m "chore: briefing $(date +%Y-%m-%dT%H:%M)" || echo "no changes"
git push origin main || echo "push skipped"
```

실행권한 부여: `chmod +x run.sh`

- [ ] **Step 2: 환경변수 예시** — `.env.example`

```bash
# 복사해서 .env 로 쓰고 값 채울 것 (.env 는 .gitignore 됨)
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
PAGES_BASE_URL=https://<github-user>.github.io/daily-briefing
BRIEF_RECIPIENT=linkpooltest2@gmail.com
```

- [ ] **Step 3: LaunchAgent 템플릿 작성** — `com.daily-briefing.plist`

`PROJECT_DIR`는 설치 시 실제 경로(`/Users/kangmin/dev/agents/daily-briefing`)로 치환.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.daily-briefing</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>PROJECT_DIR/run.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>13</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>PROJECT_DIR/.omc/brief.out.log</string>
  <key>StandardErrorPath</key><string>PROJECT_DIR/.omc/brief.err.log</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
```

> launchd는 로컬 시스템 시간대(KST 가정) 기준으로 Hour를 해석. 시스템 TZ가 KST인지 확인.

- [ ] **Step 4: README 작성** — `README.md`

```markdown
# Daily Briefing

매일 3회 데이터를 수집해 로컬 Claude Code CLI로 해석·요약하고, GitHub Pages에 배포 + 이메일 발송.

## 사전 준비
- 이 PC에 `claude` CLI 로그인 완료 (구독 사용, API 키 불필요)
- Gmail 앱 비밀번호 (Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호)
- 네이버 검색 API (developers.naver.com → 애플리케이션 등록 → 검색)
- GitHub 레포 + Pages (Settings → Pages → Deploy from branch `main` `/docs`)

## 설정
1. `cp .env.example .env` 후 값 채우기
2. `pip install -r requirements.txt`
3. `git remote add origin <your-repo>` (push 대상)

## 로컬 실행
\`\`\`bash
PAGES_BASE_URL=http://localhost python3 -m src.main --dry-run   # 이메일/배포 없이 docs/ 생성
./run.sh                                                        # 실제 생성+배포+발송
\`\`\`

## 스케줄 설치 (macOS launchd)
\`\`\`bash
sed "s|PROJECT_DIR|$(pwd)|g" com.daily-briefing.plist > ~/Library/LaunchAgents/com.daily-briefing.plist
launchctl load ~/Library/LaunchAgents/com.daily-briefing.plist
\`\`\`
하루 3회 KST 07/13/19시 실행. 해제: `launchctl unload ~/Library/LaunchAgents/com.daily-briefing.plist`
PC가 절전이면 정시 미실행 → 깨어날 때 1회 실행.

## 데이터 소스
yfinance(증시·환율), Open-Meteo(날씨), 네이버 뉴스 검색 API(경제), Google News RSS(반도체). 해석: 로컬 Claude Code CLI.
```

- [ ] **Step 5: 실행권한 + plist 문법 검증**

Run: `chmod +x run.sh && plutil -lint com.daily-briefing.plist`
Expected: `com.daily-briefing.plist: OK`

- [ ] **Step 6: 커밋**

```bash
git add run.sh .env.example com.daily-briefing.plist README.md
git commit -m "feat: launchd schedule, deploy script, docs"
```

---

## Self-Review

**1. Spec coverage:**
- 날씨 시간대별 2지역 → Task 3, Task 9 ✅
- 미국증시/반도체/한국메모리/환율 → Task 2 ✅
- 메모리 섹터 분석(Claude CLI) → Task 5 ✅
- 뉴스(네이버 경제 + Google RSS) → Task 4 ✅
- Claude CLI 해석·요약 + 폴백 → Task 5 ✅
- 웹/이메일 렌더, 이메일=요약+링크 → Task 6 ✅
- Gmail SMTP 발송 + 재시도 → Task 7 ✅
- 오케스트레이션 + archive 무한누적 + dry-run → Task 8 ✅
- impeccable 웹 디자인 → Task 9 ✅
- 로컬 launchd 3회 스케줄 + Pages 배포(run.sh git push) + .env → Task 10 ✅
- 에러 격리(collector ok 플래그) → Task 2~4, render 가드 ✅

**2. Placeholder scan:** 모든 코드/테스트/명령 실제 내용 포함. Task 9만 impeccable 산출물에 의존하나 변수 계약 명시·기존 테스트로 회귀 방지.

**3. Type consistency:** collector 반환 키(`groups`, `rates`, `locations`, `naver_economy`, `global_semi`), brief 반환(`sections`, `summary`, `degraded`), render 시그니처, main 반환(`web_path`, `archive_path`, `email_sent`) 태스크 간 일치 확인 완료.
