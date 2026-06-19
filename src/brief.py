import os
import re
import subprocess
from src import config

_SECTIONS = ("markets", "memory", "weather", "news")

# JSON 대신 마커 구분 포맷 사용: LLM이 따옴표·줄바꿈을 escape 안 해도 안전하게 파싱됨.
_PROMPT = """당신은 한국어 데일리 브리핑 애널리스트입니다.
아래 데이터를 바탕으로 투자/생활 관점의 해석을 작성하세요.

출력 형식(매우 중요):
- 아래 5개 마커 줄을 정확히 그대로 사용하고, 각 마커 아래에 해당 내용만 작성.
- 마커 줄 외의 군더더기(설명, 코드블록, 인사) 절대 금지. JSON 쓰지 말 것.
- markets/memory/news: "• "로 시작하는 짧은 불릿 3~4개, 각 불릿은 줄바꿈으로 구분, 1~2문장.
- weather: 2~3문장. summary: 이메일용 핵심 2~3문장(불릿 없이 자연스러운 문장).
- 수치·종목명은 살리되 만연체 금지.

===MARKETS===
(미국증시/M7 빅테크/반도체/한국메모리/환율 종합 해석)
===MEMORY===
(HBM/DRAM/NAND 메모리 섹터 분석)
===WEATHER===
(남양주·동탄 시간대별 날씨 요약 및 생활 팁)
===NEWS===
(경제·반도체·코스피·나스닥 시장 뉴스 핵심)
===SUMMARY===
(이메일용 전체 핵심 요약)
===END===

데이터:
{data}
"""

_MARKERS = {"MARKETS": "markets", "MEMORY": "memory",
            "WEATHER": "weather", "NEWS": "news", "SUMMARY": "summary"}


def _clean_env() -> dict:
    # 부모가 Claude Code 세션이면 CLAUDECODE/CLAUDE_CODE_* 가 주입돼
    # `claude -p`가 중첩 컨텍스트로 오작동(메타 응답)함 → 해당 변수 제거.
    return {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}


def _call_claude(prompt: str) -> str:
    # 로컬 Claude Code CLI 헤드리스 호출 (로그인된 구독 사용, API 키 불필요)
    result = subprocess.run(
        ["claude", "-p", "--model", config.SETTINGS["model"], prompt],
        capture_output=True, text=True, timeout=180, env=_clean_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr.strip()}")
    return result.stdout


def _parse(text: str):
    # ===KEY=== 마커로 분할. parts = [pre, KEY, content, KEY, content, ...]
    parts = re.split(r"===\s*(MARKETS|MEMORY|WEATHER|NEWS|SUMMARY|END)\s*===", text)
    found = {}
    for i in range(1, len(parts) - 1, 2):
        key, content = parts[i], parts[i + 1]
        if key in _MARKERS:
            found[_MARKERS[key]] = content.strip()
    sections = {s: found.get(s, "") for s in _SECTIONS}
    summary = found.get("summary", "")
    # summary와 섹션이 전부 비면 파싱 실패로 간주
    if not summary and not any(sections.values()):
        return None
    return {"sections": sections, "summary": summary}


def _fallback() -> dict:
    return {"sections": {s: "" for s in _SECTIONS},
            "summary": "(요약 생성 실패 — 수치만 표시)", "degraded": True}


def generate(raw: dict) -> dict:
    import json
    try:
        prompt = _PROMPT.format(data=json.dumps(raw, ensure_ascii=False))
        text = _call_claude(prompt)
        result = _parse(text)
        return result if result else _fallback()
    except Exception:
        return _fallback()
