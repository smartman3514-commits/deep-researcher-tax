# API_SPEC — 화면과 서버의 약속

FastAPI 서버(`server.py`), 상태는 SQLite(`executions.db`)에 저장. 모든 상태값:
`running` → `waiting_for_user` → (`done` | `rejected` | `send_failed`) | `failed`

## POST /api/briefings
새 브리핑 실행을 시작한다(에이전트를 백그라운드로 돌림).
- 응답: `{"id": "<uuid>", "status": "running"}`

## GET /api/briefings
최근 실행 50건 목록.
- 응답: `[{"id", "status", "created_at", "updated_at", "sent_at"}, ...]`

## GET /api/briefings/{id}
한 실행의 전체 상태.
- 응답: `{"id", "status", "created_at", "updated_at", "report_text", "feedback",
  "events": [...], "usage": {...} | null, "error", "sent_at"}`
- 404: 존재하지 않는 id

## POST /api/briefings/{id}/approve
사람의 결정을 반영한다. body: `{"action": "approve"|"reject"|"revise", "feedback"?: string}`
- `approve`: 상태가 `waiting_for_user`일 때만 유효. 텔레그램 발송 시도 →
  성공 시 `done`+`sent_at` 기록, 실패 시 `send_failed`+`error` 기록.
  **이미 `done`인 실행에 다시 호출하면 재발송하지 않고 그대로 반환한다(멱등성).**
- `reject`: 상태를 `rejected`로 바꾸고 끝. 아무 도구도 실행 안 됨.
- `revise`: `feedback` 필수. 상태를 `running`으로 되돌리고 에이전트를 다시 실행(피드백 반영).
- 409: `waiting_for_user`가 아닌데 approve/reject/revise를 시도한 경우
- 404: 존재하지 않는 id

## POST /api/briefings/{id}/retry_send
`send_failed` 상태에서만 유효 — 리포트를 다시 만들지 않고 발송만 재시도한다.
- 409: `send_failed`가 아닌 상태에서 호출한 경우

## 사람이 답을 기다리는 지점
`waiting_for_user`가 곧 "카드뉴스 실습" Day 39가 말한 need_input 상태다. 이 프로젝트는
질문이 여러 종류가 아니라 **승인 1종류뿐**이라 `question`/`options` 필드 없이 화면이
`report_text`를 보여주고 approve/reject/revise 버튼만 노출하는 것으로 단순화했다.
