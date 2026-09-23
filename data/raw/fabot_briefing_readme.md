# FABOT 데일리 브리핑 에이전트

Main Quest 4 제출물. 매일 FABOT 자동매매 계좌의 매매·배당 기록과 F&G 신호를 실제로 조회해
자연어 브리핑을 작성하고, **사람이 승인한 뒤에만** 텔레그램으로 발송하는 에이전틱 워크플로.

설계 배경은 PRD.md, 정한 것과 이유는 DECISIONS.md, 화면-서버 약속은 API_SPEC.md 참고.

## 실행 방법

```bash
pip install claude-agent-sdk fastapi "uvicorn[standard]" pandas numpy requests
```

1. 네이티브 Claude CLI 설치 확인 (`agent.py`의 `CLI_PATH`가 이 경로를 가리킴):
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
2. `.env.example`을 `.env`로 복사하고 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 채운다
   (fabot-auto-trade의 GitHub Actions 시크릿과 같은 값). Supabase 값은 비워두면
   `../fabot-trade-journal/.env`에서 자동으로 읽는다. **실행 이력 저장에도 이 Supabase를
   쓰므로(store.py), `supabase_briefing_executions.sql`을 그 프로젝트의 SQL Editor에서
   한 번 실행해 `briefing_executions` 테이블을 먼저 만들어야 한다.**
3. 서버 실행:
   ```bash
   python -m uvicorn server:app --port 8765
   ```
4. 브라우저에서 `http://127.0.0.1:8765` 접속.

## 구조

- `tools_impl.py` — 도구의 실제 구현(Supabase 조회, F&G 신호 판정, 텔레그램 발송).
  전부 기존 FABOT 코드(`fg-index/today_signal.py`, `fg-index/cooldown.py`,
  `fabot-auto-trade/balance_watchdog.py`)의 검증된 패턴을 그대로 재사용함.
- `agent.py` — Claude Agent SDK로 리포트 초안을 생성하는 에이전트. 읽기 전용 도구
  2개만 노출하고, 발송 도구는 아예 등록하지 않는다.
- `server.py` — FastAPI. 상태를 Supabase(`store.py`)에 저장해 새로고침·재시작·재배포
  후에도 승인 대기 화면과 이력이 그대로 복원되게 함(2026-09-10: 로컬 SQLite에서 이전 —
  Render 무료 플랜이 재배포마다 디스크를 초기화해서 이력이 사라지는 문제를 실제로 겪음).
- `static/index.html` — 브리핑 생성/실행 로그/초안/승인·거절·수정 요청/이력 화면.

## 실행 증거 (2026-09-09)

- SDK 연결 검증: `test_sdk_connection.py` 실행 → "15" 정답 수신
- 도구 단독 검증: `tools_impl.py` 직접 실행 → Supabase에서 실제 매매기록 1건, F&G 신호 조회 성공
- 에이전트 전체 실행: `agent.py` 실행 → 도구 2개 병렬 호출 → 실제 데이터로 리포트 작성,
  $0.08/17.6초/4턴
- 웹 화면 E2E: 브리핑 생성 → 승인 대기 화면 → **새로고침해도 상태 유지 확인** → 승인 클릭 →
  텔레그램 크리덴셜 미설정 상태에서 "발송 실패"로 정확히 표시 + 재시도 버튼 노출 확인

## 실패와 개선 (실제로 겪은 사례)

`fg-index/today_signal.py`의 커버드콜 쿨다운 판정이 신호상 명목 종목명
("TIGER 미국나스닥100타겟데일리커버드콜")으로 매매기록을 찾는데, 실제 매수는 세금 문제로
다른 종목("TIGER 배당커버드콜액티브")에 하고 있어서 그대로 쓰면 항상
"이전 매수 기록 없음"으로 잘못 판단했다. `fabot-auto-trade`의 실제 실행 스크립트가 쓰는
`cooldown_key` 매핑을 `tools_impl.query_fg_signal()`에도 명시적으로 적용해 고쳤고,
수정 전/후 실제 조회 결과로 차이를 확인했다(수정 전: "이전 매수 기록 없음" / 수정 후:
"마지막 매수 2026-08-28 이후 8거래일 경과").

추가로, 로컬 `price_cache.csv`가 약 한 달간 갱신되지 않아 F&G 값이 오래됐는데도
원본 모듈은 "정상 조회"로 취급하는 것을 발견해, `days_old`/`effectively_stale` 필드를
별도로 계산해 붙였다 — 에이전트가 이 필드를 보고 스스로 "데이터가 오래됐으니 승인 보류
권장"이라고 리포트에 경고까지 넣은 것을 실제 실행으로 확인했다.

## 텔레그램 실제 발송 확인 (2026-09-09)

`.env` 설정 후 승인 → 발송까지 전체 흐름 실제로 완료됨: 실행 상태가 `waiting_for_user` →
(승인) → `done`으로 바뀌고 `sent_at`이 기록됐으며, 실제 "fabot 알림봇" 대화방에 리포트가
도착한 것을 확인함. 설정 과정에서 실수 2건 발견·수정: (1) 토큰에 예시 문구의 괄호를 그대로
붙여넣어 발생한 404 오류, (2) 채팅 ID에 예시 숫자(123456789)를 그대로 둬서 발생한
"chat not found" 오류 — 둘 다 원인을 정확히 진단(에러 메시지 직접 확인)해서 고침.

## 배포 (2026-09-09)

**실제 URL: https://fabot-daily-briefing-agent.onrender.com** (Render, Docker, 무료 플랜)

배포 중 실제로 겪은 오류: 컨테이너가 기본적으로 root로 실행되는데, Claude CLI가
`--dangerously-skip-permissions`(우리 `permission_mode="bypassPermissions"`가 내부적으로
쓰는 옵션)를 보안상 root에서 거부해서 첫 배포는 모든 실행이 실패했다(Render 로그로
직접 확인: "cannot be used with root/sudo privileges"). Dockerfile에 비-root 사용자를
추가해 고쳤고, 재배포 후 실제 배포 서버에서 브리핑 생성 → 승인 → 텔레그램 발송까지
전부 성공하는 것을 직접 확인했다.

인증은 로컬 개발(D01, 이 컴퓨터의 Claude Code 로그인 재사용)과 다르게, 서버에는
대화형 로그인이 불가능해서 `claude setup-token`으로 만든 장기 토큰
(`CLAUDE_CODE_OAUTH_TOKEN`)을 Render 환경변수로 등록했다(DECISIONS.md D03 참고).

## 평가 시나리오 실행 결과

PRD 7절 시나리오 5개 전부 실제로 실행 완료. 결과: EVAL_RESULTS.md

## 하루 4번 시황 카드뉴스 (2026-09-09 확장)

PRD 10절. 승인 없이 자동으로 텔레그램 사진 메시지로 발송된다(DECISIONS.md D05).

- `market_briefing.py` — 세션별(미국장 마감/한국장 개장/한국장 마감/미국장 개장) 카드 문구 생성
- `card.py` — Pillow로 배경 사진 위에 제목·본문 텍스트 합성(1080×1350, `vendor/fonts/`의
  Noto Sans KR 사용)
- `tools_impl.search_stock_photo()` — Pexels 무료 스톡 사진 검색(D04: Antigravity/Gemini
  둘 다 실제로 결제 장벽에 부딪혀서 최종적으로 이걸 씀)
- `POST /api/scheduled/{session}?token=...` — `SCHEDULE_SECRET`으로 보호된 엔드포인트,
  cron-job.org가 이 URL을 정해진 시각에 호출하도록 설정(session: `us_close`/`kr_open`/
  `kr_close`/`us_open`, 시각은 PRD 10절 참고)

**실행 증거(2026-09-09)**: `market_briefing.py kr_close` 로컬 실행 → 실제 F&G/매매 데이터
기반 카드 문구 생성 → Pexels 실사진 검색 성공 → 카드 이미지 합성 성공. 이어서
`/api/scheduled/kr_close` 엔드포인트 실제 호출 → 텔레그램에 카드 사진 실제 발송 확인,
웹 화면 이력에서도 카드 이미지·출처가 그대로 보이는 것 확인.

**콜드스타트 대응**: cron-job.org 무료 플랜은 요청 타임아웃이 최대 30초인데, Render
무료 인스턴스가 잠들어 있으면 깨는 데만 최대 50초 걸릴 수 있어 실패할 위험이 있었다.
`/api/scheduled/*`를 `/api/briefings`(수동 생성)와 같은 방식으로 바꿔 요청을 받자마자
바로 응답하고 실제 생성·발송은 백그라운드에서 처리하도록 고쳤다 — 배포 후 실제로
193ms 만에 응답, 이후 백그라운드에서 정상 완료(텔레그램 발송·카드 저장)까지 확인함.
추가로 인스턴스가 아예 잠들지 않도록 `fabot-daily-briefing-keepalive`
cron-job(10분마다 루트 URL 핑)을 등록함(기존 `fabot-keepalive`와 같은 패턴).

**최종 스케줄 등록 완료(cron-job.org, Asia/Seoul 시간대)**:
`us_close`(**06:30**) · `kr_open`(08:00) · `kr_close`(16:00) · `us_open`(22:00),
전부 실제 서버 URL + 비밀 토큰 + POST 방식으로 확인 완료.

> **`us_close`를 07:00 → 06:30으로 변경**(2026-09-18, 사용자 요청 — 07:00은 너무 늦다).
>
> **왜 06:00이 아니라 06:30인가**: 미국장 마감은 항상 16:00 America/New_York이지만 KST로는
> 계절마다 달라진다 — 서머타임(EDT)엔 05:00 KST, 표준시(EST)엔 06:00 KST. 06:00으로 잡으면
> 겨울에 "마감하는 바로 그 순간"이 되어 쓸 내용이 없고, 해마다 두 번 시각을 바꿔야 한다.
> **06:30이면 여름엔 마감 1시간 30분 뒤, 겨울엔 30분 뒤라 사계절 그대로 둬도 된다**
> (사용자가 제안). 겨울엔 30분이라 빠듯하지만 마감 요약 기사는 보통 10~20분 안에 나온다.
>
> 시각은 이 저장소가 아니라 cron-job.org에 있으므로 코드를 고쳐도 바뀌지 않는다.

## 남은 것 (제출 시점 기준)

- 무료 인스턴스는 비활성 시 슬립되어 첫 요청이 최대 50초 정도 느릴 수 있음
  (`fabot-daily-briefing-keepalive` cron-job으로 10분마다 핑을 보내 완화함)
- cron-job.org 4개 스케줄(us_close/kr_open/kr_close/us_open) + keepalive 1개, 총 5개
  등록 완료(2026-09-10)

## 실행 이력을 Supabase로 이전 (2026-09-10)

배포 후 실제로 재배포할 때마다 웹 화면의 실행 이력이 사라지는 걸 사용자가 발견함
(로컬 SQLite가 Render 무료 플랜의 휘발성 디스크에 있었기 때문). `store.py`로 바꿔
같은 Supabase 프로젝트의 `briefing_executions` 테이블에 저장하도록 이전함 — 테이블은
`supabase_briefing_executions.sql`로 만듦(DECISIONS.md D03 참고). 이전 후 실제로
생성→승인→발송, 스케줄 브리핑, 카드 이미지 서빙까지 전부 재검증 완료.
