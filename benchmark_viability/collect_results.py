"""Step 2: Collect existing OCR benchmark results for selected documents.

Reads per-doc CSVs from benchmark/ocr/results/ and extracts
reference text, hypothesis text, and metrics for each engine×doc pair.
"""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "benchmark" / "ocr" / "results"

RESULT_CONFIGS = {
    "none": "none",
    "glm_ocr_grayscale": "glm_ocr_grayscale",
    "lighton_ocr_grayscale": "lighton_ocr_grayscale",
    "paddle_vl_grayscale": "paddle_vl_grayscale",
}


@dataclass
class DocResult:
    doc_id: str
    engine: str
    cer: float
    wer: float
    ref_text: str
    hyp_text: str
    latency: float = 0.0


def collect(doc_ids: list[str]) -> list[DocResult]:
    """Collect results for given doc_ids across all available engines."""
    results = []
    doc_set = set(doc_ids)

    seen = set()
    for _key, config_dir in RESULT_CONFIGS.items():
        csv_path = RESULTS_DIR / config_dir / "ocr_benchmark_per_doc.csv"
        if not csv_path.exists():
            continue
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                if row["doc_id"] not in doc_set:
                    continue
                eng = row.get("engine", _key)
                pair = (row["doc_id"], eng)
                if pair in seen:
                    continue
                seen.add(pair)
                results.append(DocResult(
                    doc_id=row["doc_id"],
                    engine=eng,
                    cer=float(row["cer"]),
                    wer=float(row["wer"]),
                    ref_text=row.get("_ref", ""),
                    hyp_text=row.get("_hyp", ""),
                    latency=float(row.get("latency_s", 0)),
                ))
    return results


def save_results(results: list[DocResult], out_path: Path):
    rows = [
        {"doc_id": r.doc_id, "engine": r.engine, "cer": r.cer,
         "wer": r.wer, "latency": r.latency}
        for r in results
    ]
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["doc_id", "engine", "cer", "wer", "latency"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    # Quick test with pt_train_75
    test_ids = ["xfund_train_pt_train_75"]
    results = collect(test_ids)
    for r in results:
        print(f"{r.engine:15s} CER={r.cer:.4f} WER={r.wer:.4f} ref={len(r.ref_text)}c hyp={len(r.hyp_text)}c")
