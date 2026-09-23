# 2026-09-19 추가 확정 사항 — 키움 국내/해외 모의투자는 계좌번호가 아예 다르다

**중요 발견 (재발 방지용)**: 키움증권 모의투자는 국내용과 해외용이 **서로 다른 계좌번호**로
분리돼 있다. 같은 로그인 안에 있어도 앱/화면에서 자동으로 합쳐 보여주지 않는다.
- 국내 모의투자: **국내모의계좌** — TIGER 배당커버드콜액티브 등 국내 매매가 여기 찍힘
- 해외 모의투자: **해외모의계좌** — TQQQ 등 해외 매매가 여기 찍힘

키움 모바일 앱의 "계좌 잔고" 화면은 기본으로 국내모의계좌만 보여주고, 원화/외화/모두
탭을 다 눌러봐도 해외모의계좌 내용은 안 나온다. 확인하려면 **영웅문(HTS)에서 계좌번호
드롭다운을 해외모의계좌로 직접 바꿔야** 보인다. "TQQQ가 화면에 안 보인다"는 실제 매매 실패가
아니라 이 계좌 분리 때문일 가능성을 먼저 확인할 것 — env 변수도 이 구조를 그대로 반영한다
(`KIWOOM_PAPER_APP_KEY`=국내, `KIWOOM_PAPER_OVERSEAS_APP_KEY`=해외, `kiwoom_client.py` 상단 주석).

**같은 날 발견/수정한 버그**: `get_overseas_unfilled_orders()`(ust21050, 미체결 조회)가
`stex_tp`를 빈 값으로 보내서 "거래소 구분값이 없습니다" 에러로 죽는 버그가 있었음. 09-18
02:12 KST 복구 실행(F&G 28, 25% 매수)에서 실제로는 TQQQ 343주가 정상 체결됐는데(주문번호
000006707, 총보유 359주로 확인), 체결 확인 단계에서 이 에러로 스크립트가 죽어서 매매기록
저장을 못 했음. `kiwoom_client.py`(get_overseas_balance와 동일하게 stex_tp 필수 파라미터화),
`auto_trade_loop_kiwoom.py`(이 조회가 또 실패해도 매수 자체는 막지 않도록 예외 처리 추가),
`probe_kiwoom_overseas_unfilled.py` 세 파일 수정 후 커밋 `0fd6b61`로 푸시 완료. 누락됐던
343주 매매기록은 09-19에 수동으로 Supabase `trades` 테이블에 보정(id=34, price $71.32,
fg_score 28) — 단, `log_trade()`가 `trade_date`를 항상 `date.today()`로 찍기 때문에 기록상
거래일은 실제 체결일(09-18)이 아니라 보정을 실행한 날짜(09-19)로 남아 있음(쿨다운 계산에
미세한 영향 가능, 참고만 할 것).

**연이어 발견한 별개 버그 — fabot-trade-journal 대시보드는 애초에 해외 계좌를 조회한 적이
없었음**: 위 계좌 분리 사실을 확인하고 나서도 대시보드("계좌 잔고" 카드)에 TQQQ가 계속 안
보여서 코드를 봤더니, `broker_live.js`의 `fetchKiwoomSnapshot()`이 국내 API(kt00018/kt00001)만
호출하고 해외(ust21070/ust21160) 호출 자체가 없었음 — 토큰도 국내용(`KIWOOM_PAPER_APP_KEY`)만
발급하고 있었음. KIS 쪽(`fetchKisSnapshot`)은 처음부터 해외 조회가 있었는데 Kiwoom 쪽만 빠진
구조적 공백이었던 것. `KIWOOM_PAPER_OVERSEAS_APP_KEY/SECRET`로 별도 토큰을 발급해 해외 잔고를
가져오도록 `broker_live.js`에 추가하고 로컬에서 실행 확인(TQQQ 359주 정상 반환) 후 커밋
`4a494fb`로 fabot-trade-journal에 푸시함. Render 배포 환경변수에 `KIWOOM_PAPER_OVERSEAS_APP_KEY`/
`KIWOOM_PAPER_OVERSEAS_APP_SECRET`를 사용자가 직접 추가·재배포 완료(2026-09-19) — 대시보드에
TQQQ 359주가 정상 표시되는 것까지 확인됨.
