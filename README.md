# 세금·FABOT 딥리서처 에이전트

한국 금융세제·절세계좌 문서(44건)를 기반으로, 코디네이터가 질문을 보고 관련 구역을
고르면 구역별 서브에이전트가 병렬로 조사하고, 코디네이터가 종합·점검하는 딥리서처
에이전트 실습 프로젝트. 설계와 실행 결과는 [REPORT.md](REPORT.md) 참고.

## 실행 방법

```bash
pip install claude-agent-sdk streamlit
```

1. 네이티브 Claude CLI 설치 확인:
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
2. 코퍼스 빌드(문서를 고치거나 새로 추가했을 때만 다시 실행):
   ```bash
   python build_corpus.py
   ```
3. 데모 실행:
   ```bash
   streamlit run app.py
   ```
4. 브라우저에서 `http://localhost:8502` 접속 — 예시 질문을 누르거나 직접 질문을 입력하면
   코디네이터·서브에이전트가 실시간으로 답을 만드는 과정을 볼 수 있다.

## 구조

- `graph.py` — 코디네이터-서브에이전트 파이프라인(`claude_agent_sdk` 기반, LangGraph
  없이 직접 구현). dispatch(구역 선택) → 서브에이전트 병렬 조사 → 합성 → 점검 →
  필요하면 전 구역으로 재조사.
- `app.py` — Streamlit 데모.
- `build_corpus.py` — `data/raw/*.md` 문서들을 모아 `data/corpus.json`을 만드는 스크립트.
- `data/raw/` — 원본 문서 44건(세금 10 + 계좌 9 + FABOT 로그 18 + FABOT 문서 7).
- `data/questions.json` — 평가·데모용 질문 10개.
- `metrics.py`, `ablation.py`, `baseline.py` — 평가지표, 절제실험, 대조군 비교 스크립트.
- `output/` — 위 스크립트들의 실제 실행 결과(JSON), 실측 배당 데이터 등.

## 참고

FABOT 관련 문서는 가족 실명·계좌번호를 가명 처리했다(REPORT.md 1절 참고). 상세한
설계 근거, 실측 지표, 실제로 겪은 버그·수정 과정은 [REPORT.md](REPORT.md)에 정리돼 있다.
