# 2026-09-19 추가 확정 사항 — 모의계좌 추정 배당 자동 기록 + dividend DB 제약 버그

**배경**: 모의계좌는 실제 배당이 안 나온다는 것을 실측으로 확인함(08-14 첫 매수 후 5주
지나도 커버드콜 계좌 현금이 그대로였음 — 09-09 매수 직후 약 3억 6,160만원 → 09-19에도
361,233,455원으로 사실상 동일, 배당이라면 늘었어야 함). 그래서 대시보드가 이미 쓰고 있던
가정(연 15%, `app.js`의 "예상 월 현금흐름" 계산)을 그대로 재사용해 **매달 5일에 커버드콜
(472150) 평가금액의 1.25%를 추정 배당으로 자동 기록**하기로 함(KIS+키움 두 계좌 다).
`fabot-auto-trade/estimate_dividend.py` + `.github/workflows/estimate-dividend.yml`(매월 5일
09:10 KST, GH Actions 자체 schedule만 사용 — 월간 작업이라 cron-job.org 이중화까지는
불필요하다고 판단), 커밋 `1c54f88`. 09월분은 소급으로 수동 기록(KIS 3,014,281원 / 키움
1,731,871원, trade_date 2026-09-05).

**부수적으로 발견한 버그 — dividend DB 제약이 실제로는 한 번도 적용된 적 없었음**:
`fabot-trade-journal/supabase_setup.sql`엔 2026-08-14에 `trades.action`에 'dividend'를
허용하도록 제약을 다시 만드는 마이그레이션이 적혀 있었지만, 실제 라이브 DB의 제약
(`trades_action_check`)은 여전히 `('buy','sell')`만 허용하고 있었음 — 즉 대시보드의 "+ 배당
기록 추가" 버튼은 만들어진 이후 한 번도 실제로 작동한 적이 없었던 것(눌렀다면 매번 400
에러가 났을 것). Supabase MCP는 읽기전용이라 직접 못 고치고, 사용자가 SQL Editor에서
`trades_action_check` 드롭 후 `trades_action_check_v2`(buy/sell/dividend 허용)로 재생성해
해결함(2026-09-19). **교훈**: `supabase_setup.sql`에 마이그레이션이 적혀 있다는 것이 곧 실제
DB에 적용됐다는 뜻이 아니다 — 의심되면 `pg_constraint`/`information_schema`로 라이브 DB
상태를 직접 확인할 것.
