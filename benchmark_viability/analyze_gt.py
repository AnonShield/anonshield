"""Step 0-1: Analyze XFUND-PT ground truth completeness and structure.

Extracts GT text per document, categorizes items by label type,
and identifies content vs template text.
"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

XFUND_DIR = Path(__file__).parent.parent / "benchmark" / "ocr" / "data" / "xfund_pt"


@dataclass
class GTAnalysis:
    doc_id: str
    total_items: int = 0
    total_chars: int = 0
    question_chars: int = 0
    answer_chars: int = 0
    header_chars: int = 0
    other_chars: int = 0
    answer_items: int = 0
    question_items: int = 0
    full_text: str = ""
    answers_only: str = ""
    questions_only: str = ""
    items: list = field(default_factory=list)


def load_xfund_docs() -> dict[str, list[dict]]:
    """Load all XFUND-PT documents, return {doc_id: [items]}."""
    docs = {}
    for jf in sorted(XFUND_DIR.glob("*.json")):
        data = json.loads(jf.read_text())
        doc_list = data if isinstance(data, list) else data.get("documents", [])
        for doc in doc_list:
            doc_id = f"xfund_train_{doc.get('id', doc.get('uid', ''))}"
            items = doc.get("document", doc.get("form", []))
            docs[doc_id] = items
    return docs


def analyze_doc(doc_id: str, items: list[dict]) -> GTAnalysis:
    a = GTAnalysis(doc_id=doc_id, total_items=len(items))
    answers, questions = [], []
    for item in items:
        text = item.get("text", "")
        label = item.get("label", "other")
        chars = len(text)
        a.total_chars += chars
        a.items.append({"label": label, "text": text})
        if label == "answer":
            a.answer_chars += chars
            a.answer_items += 1
            answers.append(text)
        elif label == "question":
            a.question_chars += chars
            a.question_items += 1
            questions.append(text)
        elif label == "header":
            a.header_chars += chars
        else:
            a.other_chars += chars
    a.full_text = "\n".join(item.get("text", "") for item in items if item.get("text"))
    a.answers_only = " ".join(answers)
    a.questions_only = " ".join(questions)
    return a


def main():
    docs = load_xfund_docs()
    print(f"Loaded {len(docs)} XFUND-PT documents\n")

    analyses = []
    for doc_id, items in sorted(docs.items()):
        analyses.append(analyze_doc(doc_id, items))

    print(f"{'doc_id':>40s}  items  chars  ans_items  ans_chars  q_chars  ans%")
    print("-" * 110)
    for a in sorted(analyses, key=lambda x: x.answer_chars, reverse=True):
        ans_pct = a.answer_chars / a.total_chars * 100 if a.total_chars else 0
        print(f"{a.doc_id:>40s}  {a.total_items:5d}  {a.total_chars:5d}  "
              f"{a.answer_items:9d}  {a.answer_chars:9d}  {a.question_chars:7d}  {ans_pct:5.1f}%")

    # Summary stats
    total_docs = len(analyses)
    avg_items = sum(a.total_items for a in analyses) / total_docs
    avg_ans_pct = sum(
        a.answer_chars / a.total_chars * 100 for a in analyses if a.total_chars
    ) / total_docs
    print(f"\nSummary: {total_docs} docs, avg {avg_items:.0f} items/doc, "
          f"avg answer content {avg_ans_pct:.1f}%")

    # Select 10 representative docs for viability test
    by_ans = sorted(analyses, key=lambda x: x.answer_chars, reverse=True)
    heavy = [a.doc_id for a in by_ans[:4]]
    light = [a.doc_id for a in by_ans[-3:] if a.answer_chars > 0]
    mid_start = len(by_ans) // 2 - 1
    mid = [a.doc_id for a in by_ans[mid_start:mid_start + 3]]
    selected = heavy + mid + light

    # Always include pt_train_75
    target = "xfund_train_pt_train_75"
    if target not in selected:
        selected = [target] + selected[:9]

    print(f"\nSelected {len(selected)} docs for viability test:")
    for d in selected:
        a = next(x for x in analyses if x.doc_id == d)
        print(f"  {d} — {a.answer_items} answers, {a.answer_chars} answer chars")

    return selected, {a.doc_id: a for a in analyses}


if __name__ == "__main__":
    main()
