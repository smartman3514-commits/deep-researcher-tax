"""raw/ 밑의 마크다운 문서들을 읽어서 data/corpus.json 하나로 합친다.
문서가 30건 넘게 흩어져 있어야 하는 실습 요구사항이라, 카테고리는 파일명 접두어로
기계적으로 분류한다(수동으로 매번 태깅하면 문서가 늘 때마다 깨지기 쉬움).
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
RAW = BASE / "data" / "raw"


def category_for(stem: str) -> str:
    if stem.startswith("fabot_log_"):
        return "fabot_log"
    if stem.startswith("fabot_"):
        return "fabot_doc"
    if stem in {
        "isa_account", "pension_savings_account", "irp_account",
        "retirement_pension_system", "dividend_tax_exemption_requirements",
        "etf_taxation_classification", "income_deduction_vs_tax_credit",
        "comprehensive_income_tax_filing_criteria", "family_income_splitting_legality",
    }:
        return "account"
    return "tax_law"


def title_for(text: str, stem: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return stem


def main():
    docs = []
    for path in sorted(RAW.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        stem = path.stem
        docs.append({
            "id": stem,
            "title": title_for(text, stem),
            "category": category_for(stem),
            "text": text.strip(),
            "n_chars": len(text),
        })
    out = {"documents": docs}
    (BASE / "data" / "corpus.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    by_cat = {}
    for d in docs:
        by_cat[d["category"]] = by_cat.get(d["category"], 0) + 1
    total_chars = sum(d["n_chars"] for d in docs)
    print(f"문서 {len(docs)}건, 총 {total_chars:,}자")
    for cat, n in by_cat.items():
        print(f"  - {cat}: {n}건")


if __name__ == "__main__":
    main()
