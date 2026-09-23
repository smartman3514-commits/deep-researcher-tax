"""정답표 없이 재는 평가지표. 정답을 모르니 "내용이 맞았는지"는 못 재고,
대신 구조적으로 확인 가능한 것만 잰다(수업에서 배운 "넷 vs 자" 구분 그대로 —
이 지표들은 net이지 ruler가 아니다. 즉 뻔한 실패는 잡지만, 답이 사실관계까지
맞는지는 사람이 직접 읽어야 한다).

- 구역 재현율(recall): 질문에 실제로 필요한 구역을 다 조사했는가
- 구역 정밀도(precision): 불필요한 구역까지 과하게 조사하지 않았는가
- 인용 유효성: 답변이 인용한 문서 id가 실제 코퍼스에 존재하는가(허위 인용 방지)
- 근거율: 조사한 문서 중 실제로 인용에 쓰인 비율(읽고 안 쓴 문서가 얼마나 되는지)
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
CORPUS_IDS = {d["id"] for d in json.loads((BASE / "data" / "corpus.json").read_text(encoding="utf-8"))["documents"]}


def extract_cited_ids(answer_text: str) -> set[str]:
    """"(근거 문서: id1, id2)" 형식에서 실제로 인용된 문서 id를 뽑는다."""
    cited = set()
    for m in re.finditer(r"근거\s*문서\s*[:：]\s*([^)]+)\)", answer_text):
        for token in re.split(r"[,\s]+", m.group(1)):
            token = token.strip()
            if token in CORPUS_IDS:
                cited.add(token)
    return cited


def score_result(result: dict, requires_categories: list[str]) -> dict:
    dispatched = set(result["categories_used"])
    required = set(requires_categories)
    cited = extract_cited_ids(result["answer"])

    recall = len(dispatched & required) / len(required) if required else 1.0
    precision = len(dispatched & required) / len(dispatched) if dispatched else 0.0

    all_ids_in_dispatched = {
        d["id"] for d in json.loads((BASE / "data" / "corpus.json").read_text(encoding="utf-8"))["documents"]
        if d["category"] in dispatched
    }
    invalid_citations = cited - CORPUS_IDS  # 있을 수 없음(파싱 자체가 CORPUS_IDS로 필터하니 참고용)
    used_ratio = len(cited) / len(all_ids_in_dispatched) if all_ids_in_dispatched else 0.0

    return {
        "category_recall": round(recall, 3),
        "category_precision": round(precision, 3),
        "n_cited_docs": len(cited),
        "n_docs_investigated": len(all_ids_in_dispatched),
        "cited_doc_usage_ratio": round(used_ratio, 3),
        "n_invalid_citations": len(invalid_citations),
    }


def run_all():
    import graph
    questions = json.loads((BASE / "data" / "questions.json").read_text(encoding="utf-8"))["items"]
    rows = []
    for q in questions:
        result = graph.answer(q["question"])
        m = score_result(result, q.get("requires_categories", []))
        rows.append({"id": q["id"], "question": q["question"], "difficulty": q["difficulty"],
                     "categories_used": result["categories_used"],
                     "requires_categories": q.get("requires_categories", []), **m})
        print(f"[{q['id']}] recall={m['category_recall']} precision={m['category_precision']} "
              f"근거율={m['cited_doc_usage_ratio']} 무효인용={m['n_invalid_citations']}")

    out = {"rows": rows,
           "avg_recall": round(sum(r["category_recall"] for r in rows) / len(rows), 3),
           "avg_precision": round(sum(r["category_precision"] for r in rows) / len(rows), 3),
           "avg_citation_usage": round(sum(r["cited_doc_usage_ratio"] for r in rows) / len(rows), 3)}
    (BASE / "output" / "metrics.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n평균 구역 재현율={out['avg_recall']}, 평균 정밀도={out['avg_precision']}, "
          f"평균 근거 활용률={out['avg_citation_usage']}")
    print("output/metrics.json 저장 완료")


if __name__ == "__main__":
    run_all()
