"""공정한 대조군 비교 — "코디네이터+서브에이전트 구조" vs "단일 LLM 한 번 호출".

공정성 조건(둘 다 동일):
- 같은 모델(config.json의 synthesis_model)
- 같은 코퍼스 전체(단일 LLM도 전체 문서를 다 받는다 — 일부러 코퍼스를 줄여서
  단일 LLM이 불리하게 만들지 않는다)
- 같은 질문 세트(data/questions.json 10문항)
- 같은 채점 기준(metrics.py)

차이는 오직 구조 하나: 구역별로 나눠서 병렬로 조사한 뒤 합치는가(구조),
아니면 통째로 한 번에 읽고 바로 답하는가(단일 LLM)다.
"""
import json
from pathlib import Path

import graph
import metrics

BASE = Path(__file__).parent
_ALL_QUESTIONS = json.loads((BASE / "data" / "questions.json").read_text(encoding="utf-8"))["items"]
# ablation.py와 같은 이유로 5문항 부분집합만 쓴다(실행 시간 단축) — metrics.py가
# 전체 10문항 채점은 이미 커버함.
QUESTIONS = [q for q in _ALL_QUESTIONS if q["id"] in {"q01", "q03", "q05", "q06", "q08"}]


def run(label: str, single_llm: bool) -> list[dict]:
    graph.CONFIG["ablation"] = {
        "disable_dispatch_routing": False, "disable_review_loop": False,
        "single_llm_only": single_llm,
    }
    rows = []
    for q in QUESTIONS:
        result = graph.answer(q["question"])
        m = metrics.score_result(result, q.get("requires_categories", []))
        rows.append({"id": q["id"], "difficulty": q["difficulty"], "label": label, **m})
        print(f"[{label}/{q['id']}] recall={m['category_recall']} 근거활용률={m['cited_doc_usage_ratio']}")
    return rows


def main():
    pipeline_rows = run("multi_agent_pipeline", single_llm=False)
    baseline_rows = run("single_llm_baseline", single_llm=True)

    def avg(rows, key):
        return round(sum(r[key] for r in rows) / len(rows), 3)

    summary = {
        "multi_agent_pipeline": {
            "avg_recall": avg(pipeline_rows, "category_recall"),
            "avg_citation_usage": avg(pipeline_rows, "cited_doc_usage_ratio"),
        },
        "single_llm_baseline": {
            "avg_recall": avg(baseline_rows, "category_recall"),
            "avg_citation_usage": avg(baseline_rows, "cited_doc_usage_ratio"),
        },
    }
    (BASE / "output" / "baseline_comparison.json").write_text(
        json.dumps({"summary": summary, "rows": pipeline_rows + baseline_rows},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== 요약 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\noutput/baseline_comparison.json 저장 완료")


if __name__ == "__main__":
    main()
