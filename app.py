"""데모 화면 — 질문을 넣으면 코디네이터가 구역을 고르고, 서브에이전트들이 병렬로
조사한 뒤, 합쳐서 답하는 과정을 그대로 보여준다. 실행: streamlit run app.py
"""
import json
import os
from pathlib import Path

import streamlit as st

# Streamlit Community Cloud 배포 시 st.secrets로 CLAUDE_CODE_OAUTH_TOKEN을 받는데,
# secrets.toml이 아예 없는 로컬 환경에서는 st.secrets 접근 자체가 예외를 던진다
# (my-graph-agent/app.py에서 실제로 겪은 문제와 동일한 방어).
try:
    has_oauth_secret = "CLAUDE_CODE_OAUTH_TOKEN" in st.secrets
except Exception:
    has_oauth_secret = False
if has_oauth_secret:
    os.environ.setdefault("CLAUDE_CODE_OAUTH_TOKEN", st.secrets["CLAUDE_CODE_OAUTH_TOKEN"])

import graph

BASE = Path(__file__).parent

st.set_page_config(page_title="세금·FABOT 딥리서처 에이전트", page_icon="🔎")
st.title("🔎 세금·FABOT 딥리서처 에이전트")
st.caption("딥리서처 에이전트 실습 프로젝트 — 한국 금융세제·절세계좌 44개 문서 기반 코디네이터-서브에이전트 질의응답")

with st.expander("이 데모에 대해", expanded=False):
    st.markdown(
        """
        - **코퍼스**: `data/corpus.json` — 세금 10건 + 계좌 9건(위키백과·국세청 등 공개 자료
          재서술) + FABOT 자동매매 프로젝트 실제 기록 25건(가명 처리), 총 44건
        - **세금 10건 중 하나**는 [미래에셋자산운용 TIGER ETF 공식 사이트](https://investments.miraeasset.com/tigeretf/ko/main/index.do)의
          과세 안내 문구와, 사용자가 그 사이트에서 직접 내려받은 TIGER 배당커버드콜액티브
          상장 이후 33개월 실제 분배금·과표증분 지급현황 전체를 반영해서 만들었어요
          (`etf_distribution_taxable_base_cap`) — 실측 데이터가 실제로 답을 15~30배
          바꾼 사례예요.
        - **구조**: 코디네이터가 질문을 보고 관련 구역(세금/계좌/FABOT 로그/FABOT 문서)을 고른 뒤,
          구역별 서브에이전트가 병렬로 조사 → 코디네이터가 합성 → 점검해서 부족하면 전 구역으로 재조사
        - 아래 예시 질문을 눌러서 바로 실행해볼 수 있어요.
        """
    )

questions = json.loads((BASE / "data" / "questions.json").read_text(encoding="utf-8"))["items"]
example_qs = [item["question"] for item in questions]

# 기본 st.button은 라벨을 한 줄로만 표시해서 긴 질문이 "..."로 잘린다 — 질문 전체가
# 읽혀야 어떤 예시를 고를지 판단할 수 있으므로 버튼 라벨이 줄바꿈되게 CSS로 푼다.
st.markdown(
    """
    <style>
    div[data-testid="stButton"] button {
        white-space: normal !important;
        height: auto;
        text-align: left;
        line-height: 1.4;
    }
    div[data-testid="stButton"] button p,
    div[data-testid="stButton"] button div {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

question = st.text_area(
    "질문을 입력하세요",
    value=st.session_state.get("q", ""),
    placeholder="무엇을 도와드릴까요?",
    height=80,
)
# 버튼 자리를 비워두고, 실행 중에는 같은 자리에 "답변 중입니다"(비활성) 버튼을 대신 그린다 —
# 눌렀는데 버튼이 그대로면 반응했는지 모르겠다는 피드백 반영.
button_slot = st.empty()
run = button_slot.button("질문하기", type="primary", key="ask")

# 결과 영역을 버튼 바로 아래, 예시 질문 목록보다 위에 둔다 — 예전엔 예시 질문 그리드
# 밑에 있어서 "질문하기"를 눌러도 스크롤해야만 반응(스피너)이 보였다(실사용 중 발견).
result_area = st.container()

st.caption("또는 아래 예시 질문 중 하나를 눌러도 바로 실행됩니다:")
cols = st.columns(2)
for i, q in enumerate(example_qs):
    if cols[i % 2].button(q, key=f"ex-{i}", use_container_width=True):
        st.session_state["q"] = q
        st.rerun()

if run or question:
    button_slot.button("⏳ 답변 중입니다...", type="primary", disabled=True, key="ask_busy")
    with result_area:
        with st.status("코디네이터가 질문을 처리하는 중... (보통 30초~2분 걸려요)", expanded=True) as status:
            result = graph.answer(question, on_step=lambda msg: status.update(label=msg))
            status.update(label="완료", state="complete")

        st.subheader("탄 경로")
        st.code(result["trace"], language=None)
        st.write("조사한 구역:", ", ".join(result["categories_used"]))

        st.subheader("답변")
        st.markdown(result["answer"].replace("\n", "  \n"))

        st.subheader("서브에이전트별 부분 답변")
        for p in result["subagent_outputs"]:
            with st.expander(f"구역: {p['category']}"):
                st.markdown(p["output"].replace("\n", "  \n"))

    button_slot.button("질문하기", type="primary", key="ask_again")

st.divider()
st.caption(
    "평가·절제실험 결과가 궁금하면 터미널에서 `python metrics.py`, "
    "`python ablation.py`, `python baseline.py`를 실행하세요."
)
