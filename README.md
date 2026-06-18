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
```bash
PAGES_BASE_URL=http://localhost .venv/bin/python -m src.main --dry-run   # 이메일/배포 없이 docs/ 생성
./run.sh                                                        # 실제 생성+배포+발송
```

## 스케줄 설치 (macOS launchd)
```bash
sed "s|PROJECT_DIR|$(pwd)|g" com.daily-briefing.plist > ~/Library/LaunchAgents/com.daily-briefing.plist
launchctl load ~/Library/LaunchAgents/com.daily-briefing.plist
```
하루 3회 KST 07/13/19시 실행. 해제: `launchctl unload ~/Library/LaunchAgents/com.daily-briefing.plist`
PC가 절전이면 정시 미실행 → 깨어날 때 1회 실행.

## 데이터 소스
yfinance(증시·환율), Open-Meteo(날씨), 네이버 뉴스 검색 API(경제), Google News RSS(반도체). 해석: 로컬 Claude Code CLI.
