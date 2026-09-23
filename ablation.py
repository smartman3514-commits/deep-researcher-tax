"""절제실험 — 구조의 각 장치를 하나씩 꺼서, 그게 실제로 결과에 영향을 주는지 확인한다.

- full: 기본 구조(dispatch 라우팅 + 서브에이전트 병렬 + 점검 루프) 그대로
- no_routing: dispatch가 구역을 안 고르고 항상 전 구역에 뿌림(라우팅이 실제로 도움이 되는지)
- no_review: 점검 없이 첫 합성 결과를 그대로 최종 답으로 씀(점검 루프가 실제로 잡아내는 게 있는지)
- single_llm: 코디네이터/서브에이전트 구조 자체를 없애고 전체 코퍼스를 한 번에 통째로 던짐
  (구조 자체가 baseline.py의 단일 LLM 방식과 동일 — 여기서는 "구조를 껐을 때" 관점으로 다시 잰다)

비용(시간·API 호출 수) 대비 품질(metrics.py 지표) 변화를 비교한다.
"""
import json
import time
from pathlib import Path

import graph
import metrics

BASE = Path(__file__).parent
_ALL_QUESTIONS = json.loads((BASE / "data" / "questions.json").read_text(encoding="utf-8"))["items"]
# 조건 4개 × 전체 10문항은 claude_agent_sdk 호출이 너무 많이 쌓여 실행 시간이 길다
# (실측: 40문항 도중 일시적 SDK 오류도 겪음). 절제실험은 난이도별로 하나씩 뽑은
# 5문항 부분집합으로 돌린다 — 전체 채점은 metrics.py가 이미 10문항 다 커버한다.
QUESTIONS = [q for q in _ALL_QUESTIONS if q["id"] in {"q01", "q03", "q05", "q06", "q08"}]

CONDITIONS = {
    "full": {},
    "no_routing": {"disable_dispatch_routing": True},
    "no_review": {"disable_review_loop": True},
    "single_llm": {"single_llm_only": True},
}


def run_condition(name: str, ablation_flags: dict) -> dict:
    graph.CONFIG["ablation"] = {
        "disable_dispatch_routing": False,
        "disable_review_loop": False,
        "single_llm_only": False,
        **ablation_flags,
    }
    rows = []
    t0 = time.time()
    for q in QUESTIONS:
        result = graph.answer(q["question"])
        m = metrics.score_result(result, q.get("requires_categories", []))
        n_calls = 1 if ablation_flags.get("single_llm_only") else (
            1 + len(result["categories_used"]) + 1  # dispatch + subagents + aggregate
            + (0 if graph.CONFIG["ablation"]["disable_review_loop"] else 1)
        )
        rows.append({"id": q["id"], "n_llm_calls": n_calls, **m})
    elapsed = time.time() - t0
    return {
        "condition": name,
        "elapsed_sec": round(elapsed, 1),
        "avg_llm_calls_per_question": round(sum(r["n_llm_calls"] for r in rows) / len(rows), 2),
        "avg_recall": round(sum(r["category_recall"] for r in rows) / len(rows), 3),
        "avg_precision": round(sum(r["category_precision"] for r in rows) / len(rows), 3),
        "avg_citation_usage": round(sum(r["cited_doc_usage_ratio"] for r in rows) / len(rows), 3),
        "avg_invalid_citations": round(sum(r["n_invalid_citations"] for r in rows) / len(rows), 3),
        "rows": rows,
    }


def main():
    results = []
    for name, flags in CONDITIONS.items():
        print(f"\n=== {name} 실행 중 ===")
        r = run_condition(name, flags)
        results.append(r)
        print(f"{name}: 평균 호출수={r['avg_llm_calls_per_question']}, 재현율={r['avg_recall']}, "
              f"정밀도={r['avg_precision']}, 근거활용률={r['avg_citation_usage']}, "
              f"소요={r['elapsed_sec']}초")

    (BASE / "output" / "ablation_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\noutput/ablation_results.json 저장 완료")


if __name__ == "__main__":
    main()
