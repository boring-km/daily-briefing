# Daily Briefing — Design Spec

**Date:** 2026-06-19
**Project path:** `/Users/kangmin/dev/agents/daily-briefing`

## 목적

레퍼런스 사이트(https://ai-assistant-minhyuk.vercel.app/)와 유사한 AI 데일리 브리핑을
자동 생성하여 (1) 웹에 배포하고 (2) 요약을 이메일로 발송한다. 하루 3회 자동 실행.

## 산출물

- **웹**: GitHub Pages에 배포되는 전체 상세 브리핑 (impeccable 디자인)
- **이메일**: 핵심 요약 + "웹에서 자세히 보기" 링크 (Gmail SMTP)

## 콘텐츠 구성

레퍼런스 구성 + 추가 항목.

| 섹션 | 내용 | 소스 |
|---|---|---|
| 날씨 | 남양주시·동탄 **시간대별 1시간 단위** 예보 | Open-Meteo (키리스) |
| 미국 증시 | S&P500(^GSPC), NASDAQ(^IXIC), SOX(^SOX) | yfinance |
| 반도체 | NVDA, AMD, MU(Micron), TSM 등 등락 + 뉴스 | yfinance + Google News RSS |
| 메모리 섹터 분석 | HBM/DRAM/NAND 해석 | Claude (해석 생성) |
| 한국 메모리 | 삼성전자(005930.KS), SK하이닉스(000660.KS) | yfinance |
| **환율** (추가) | USD/KRW 등 주요 환율 | yfinance (KRW=X) |
| **일반/경제 뉴스** (추가) | 국내 경제 위주 + 세계 주요 헤드라인 | 네이버 뉴스 검색 API + Google News RSS |

- 해석/분석/요약 텍스트는 **Claude API (sonnet)** 가 생성.
- 뉴스 소스 2종:
  - **네이버 뉴스 검색 API** — 국내 **경제 위주** 헤드라인 (무료키, 신선, 25,000req/day). 키: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`.
  - **Google News RSS** — 반도체/글로벌 뉴스 (키리스·실시간).

## 아키텍처

```
src/
├── collectors/      # 데이터 수집 (소스별 1파일, 독립 실행 가능)
│   ├── stocks.py    # 미국증시·반도체·한국메모리
│   ├── fx.py        # 환율
│   ├── weather.py   # 남양주·동탄 시간대별
│   └── news.py      # 반도체뉴스 + 일반뉴스
├── brief.py         # Claude로 섹션 해석 + 이메일용 요약 생성
├── render.py        # 웹 HTML + 이메일 HTML 렌더 (templates 사용)
├── mailer.py        # Gmail SMTP 발송
└── main.py          # 오케스트레이션 (--dry-run 지원)
templates/           # impeccable 디자인 (web.html.j2, email.html.j2)
docs/                # GitHub Pages 배포 대상
├── index.html       # 최신 브리핑
└── archive/         # 과거 브리핑 (YYYY-MM-DD-HHmm.html, 무한 누적)
.github/workflows/brief.yml
tests/
requirements.txt
README.md
```

### 컴포넌트 책임 (단위별 1목적)

- **collectors/\***: 외부 소스 → 정규화된 dict 반환. 네트워크/파싱만 담당, 해석 없음.
  의존: 해당 라이브러리/HTTP. 인터페이스: `collect() -> dict`.
- **brief.py**: 수집 dict → Claude 호출 → `{sections: {...해석...}, summary: "..."}` 반환.
  의존: anthropic SDK. collectors를 모름(dict만 받음).
- **render.py**: 데이터 + 해석 → 웹/이메일 HTML 문자열. 의존: jinja2 + templates.
- **mailer.py**: HTML + 수신자 → 발송. 의존: smtplib. 콘텐츠를 모름.
- **main.py**: 위를 순서대로 호출, 파일 출력, 에러 격리.

## 데이터 흐름

1. `main.py`가 각 collector 호출 → `raw` dict 수집
2. `brief.py`가 `raw`를 Claude에 전달 → 섹션별 해석 + 이메일 요약 생성
3. `render.py`:
   - 웹 HTML (전체 상세, 시간대별 날씨 등) → `docs/index.html` + `docs/archive/<ts>.html`
   - 이메일 HTML (요약 + Pages 링크)
4. git commit/push → GitHub Pages 자동 배포
5. `mailer.py`가 요약 이메일 발송

## 스케줄 & 배포

- **실행**: GitHub Actions cron, 하루 3회
  - KST 07:00 / 13:00 / 19:00 = UTC 22:00 / 04:00 / 10:00
  - cron: `0 22,4,10 * * *`
- **웹 배포**: Actions가 `docs/` 커밋·푸시 → GitHub Pages가 `/docs` 서빙
- **Pages URL**: `https://<github-user>.github.io/<repo>/` (이메일 링크에 사용)

> 참고: 원래 "이 PC에서" 요구였으나 GitHub Actions 선택으로 클라우드 실행됨(PC 꺼져도 동작). 로컬 실행이 필요하면 launchd 백업 스케줄 추가 가능.

## 비밀키 (GitHub Secrets)

- `ANTHROPIC_API_KEY` — Claude API
- `GMAIL_USER` — 발송 Gmail 주소
- `GMAIL_APP_PASSWORD` — Gmail 앱 비밀번호 (2단계 인증 후 발급)
- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` — 네이버 뉴스 검색 API
- 수신: `linkpooltest2@gmail.com` (발송=수신 동일)

## 에러 처리

- collector 개별 실패: try/except로 격리, 해당 섹션 "데이터 없음" 표기 후 나머지 진행
- Claude 호출 실패: 원본 데이터만으로 폴백 렌더 (해석 없이 수치만)
- 이메일 발송 실패: 로그 기록 + 재시도 1회, 그래도 실패 시 Actions 잡 실패 처리
- 웹 배포는 이메일과 독립 — 한쪽 실패가 다른 쪽 막지 않음

## 테스트

- collector 단위: mock HTTP/응답으로 파싱 검증
- render 스냅샷: 생성 HTML에 필수 섹션 모두 존재 확인
- 통합: `python -m src.main --dry-run` (이메일·배포 없이 HTML만 로컬 생성)

## 웹 디자인

impeccable 스킬로 웹 템플릿 디자인 (구현 단계에서 적용):
- 레퍼런스보다 다듬어진 대시보드 레이아웃
- 시간대별 날씨를 시각화 (1시간 단위 차트/타임라인)
- 섹션 카드 구조, 한국어 타이포그래피, 다크/라이트 고려

## 범위 밖 (YAGNI)

- 사용자 인증/다중 사용자
- 과거 브리핑 검색 UI (archive는 파일로만 누적)
- 모바일 앱
- 캘린더/코인 등 1차 범위에서 제외한 항목 (추후 확장 가능)
