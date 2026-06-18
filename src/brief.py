import json
import subprocess
from src import config

_SECTIONS = ("markets", "memory", "weather", "news")

_PROMPT = """당신은 한국어 데일리 브리핑 애널리스트입니다.
아래 JSON 데이터를 바탕으로 투자/생활 관점의 해석을 작성하세요.
반드시 아래 형식의 JSON만 출력하세요(설명 금지):
{{"sections": {{"markets": "...", "memory": "...", "weather": "...", "news": "..."}}, "summary": "..."}}

가독성 규칙(중요):
- markets/memory/news 섹션은 한 덩어리 만연체 금지. 핵심별 3~4개의 짧은 불릿으로 작성.
- 각 불릿은 "• "로 시작, 불릿 사이는 줄바꿈 문자 \\n 로 구분. 한 불릿은 1~2문장.
- weather는 2~3문장. summary는 이메일용이라 2~3문장 자연스러운 문장(불릿 불필요).
- 수치/종목명은 살리되 간결하게.

각 섹션 내용:
- markets: 미국증시/M7 빅테크/반도체/한국메모리/환율 종합 해석
- memory: HBM/DRAM/NAND 메모리 섹터 분석
- weather: 남양주·동탄 시간대별 날씨 요약 및 생활 팁
- news: 경제·반도체·코스피·나스닥 시장 뉴스 핵심
- summary: 이메일용 전체 핵심 요약 (가장 중요한 것만)

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
