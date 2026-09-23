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
st.caption("딥리서처 에이전트 실습 프로젝트 — 한국 금융세제·절세계좌 43개 문서 기반 코디네이터-서브에이전트 질의응답")

with st.expander("이 데모에 대해", expanded=False):
    st.markdown(
        """
        - **코퍼스**: `data/corpus.json` — 세금 9건 + 계좌 9건(위키백과·국세청 등 공개 자료 재서술)
          + FABOT 자동매매 프로젝트 실제 기록 25건(가명 처리), 총 43건
        - **구조**: 코디네이터가 질문을 보고 관련 구역(세금/계좌/FABOT 로그/FABOT 문서)을 고른 뒤,
          구역별 서브에이전트가 병렬로 조사 → 코디네이터가 합성 → 점검해서 부족하면 전 구역으로 재조사
        - 아래 예시 질문을 눌러서 바로 실행해볼 수 있어요.
        """
    )

questions = json.loads((BASE / "data" / "questions.json").read_text(encoding="utf-8"))["items"]
example_qs = [item["question"] for item in questions]

col1, col2 = st.columns([3, 1])
with col1:
    question = st.text_input("질문을 입력하세요", value=st.session_state.get("q", example_qs[2]))
with col2:
    st.write("")
    st.write("")
    run = st.button("질문하기", type="primary", use_container_width=True)

st.caption("예시 질문 (클릭하면 바로 채워집니다):")
cols = st.columns(2)
for i, q in enumerate(example_qs):
    if cols[i % 2].button(q, key=f"ex-{i}", use_container_width=True):
        st.session_state["q"] = q
        st.rerun()

if run or question:
    with st.spinner("코디네이터가 구역을 나누고 서브에이전트를 실행하는 중..."):
        result = graph.answer(question)

    st.subheader("탄 경로")
    st.code(result["trace"], language=None)
    st.write("조사한 구역:", ", ".join(result["categories_used"]))

    st.subheader("답변")
    st.markdown(result["answer"].replace("\n", "  \n"))

    st.subheader("서브에이전트별 부분 답변")
    for p in result["subagent_outputs"]:
        with st.expander(f"구역: {p['category']}"):
            st.markdown(p["output"].replace("\n", "  \n"))

st.divider()
st.caption(
    "평가·절제실험 결과가 궁금하면 터미널에서 `python metrics.py`, "
    "`python ablation.py`, `python baseline.py`를 실행하세요."
)
