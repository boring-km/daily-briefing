#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# .env 로드 (GMAIL_*, NAVER_*, PAGES_BASE_URL, BRIEF_RECIPIENT)
set -a
[ -f .env ] && . ./.env
set +a

# 절전 방지하며 실행 (최대 10분)
caffeinate -i .venv/bin/python -m src.main

# 웹 배포: docs 변경분 커밋·푸시 → GitHub Pages
git add docs/
git commit -m "chore: briefing $(date +%Y-%m-%dT%H:%M)" || echo "no changes"
git push origin main || echo "push skipped"
