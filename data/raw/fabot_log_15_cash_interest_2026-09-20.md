# 2026-09-20 추가 확정 사항 — 현금 예수금 추정 이자(연 3%) 자동 기록

모의계좌는 현금(예수금)에도 실제 이자가 안 붙는다. 배당(estimate_dividend.py)과 같은 논리로,
**매달 3일에 KIS/키움 현금 잔고(원화+달러 환산)의 연 3%를 월할(0.25%) 계산해서 추정 이자로
자동 기록**하기로 함. `fabot-auto-trade/estimate_interest.py` +
`.github/workflows/estimate-interest.yml`(매월 3일 09:10 KST), 커밋 `be57ebb`.

- 기록 방식: 배당과 똑같이 `trades.action="dividend"`로 저장하되 `ticker="현금(이자)"`로
  구분한다 — 대시보드가 이미 action=dividend를 총수익·장기추이 차트에 전부 집계하는 로직을
  그대로 타서, 이자도 별도 코드 없이 자동으로 총수익에 포함된다. 표에서만 배당과 이자를
  별도 줄로 나눠 보여준다(`fabot-trade-journal/public/app.js`, 커밋 `6638ea8`).
- 현금 계산: KIS는 국내 예수금(dnca_tot_amt)+해외 달러 예수금(inquire-psamount의
  ord_psbl_frcr_amt)×환율, 키움은 국내 예수금(kt00001 ord_alow_amt)+해외 달러 예수금
  (ust21160, T+2~3 결제 지연을 고려해 정산 완료된 d4→d0 필드 중 값이 있는 것)×환율 —
  환율은 1380.3 고정 근사치(대시보드의 CASH_RECONSTRUCTION과 동일 기준).
- 2026-09-20 실측(dry-run): KIS 현금 약 3억 6,163만원 → 월 이자 약 90.4만원, 키움 현금 약
  4억 6,397만원 → 월 이자 약 116.0만원.
