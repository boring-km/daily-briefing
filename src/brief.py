import json
import subprocess
from src import config

_SECTIONS = ("markets", "memory", "weather", "news")

_PROMPT = """당신은 한국어 데일리 브리핑 애널리스트입니다.
아래 JSON 데이터를 바탕으로 투자/생활 관점의 간결한 해석을 작성하세요.
반드시 아래 형식의 JSON만 출력하세요(설명 금지):
{{"sections": {{"markets": "...", "memory": "...", "weather": "...", "news": "..."}}, "summary": "..."}}
- markets: 미국증시/M7 빅테크/반도체/한국메모리/환율 종합 해석 (3~5문장)
- memory: HBM/DRAM/NAND 메모리 섹터 분석 (2~4문장)
- weather: 남양주·동탄 시간대별 날씨 요약 및 생활 팁 (2~3문장)
- news: 경제·반도체·코스피·나스닥 시장 뉴스 핵심 (3~4문장)
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
