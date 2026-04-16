#!/usr/bin/env python3
"""Full viability test pipeline.

Executes steps 0-5 of the BRACIS paper viability test:
  0. Analyze GT structure for all 199 docs
  1. Select 10 representative docs
  2. Collect existing OCR results
  3. Compute multi-variant CER metrics
  4. Check for ranking inversion
  5. Generate decision report
"""
import csv
import statistics
from pathlib import Path

from analyze_gt import load_xfund_docs, analyze_doc
from collect_results import collect, RESULTS_DIR
from compute_metrics import compute_all

OUT_DIR = Path(__file__).parent / "output"


def step0_analyze_gt():
    """Analyze all XFUND-PT documents GT structure."""
    print("=" * 80)
    print("STEP 0: Analyzing XFUND-PT Ground Truth Structure")
    print("=" * 80)

    docs = load_xfund_docs()
    analyses = {doc_id: analyze_doc(doc_id, items) for doc_id, items in docs.items()}

    total = len(analyses)
    avg_items = sum(a.total_items for a in analyses.values()) / total
    avg_ans_pct = sum(
        a.answer_chars / a.total_chars * 100
        for a in analyses.values() if a.total_chars
    ) / total
    avg_ans_items = sum(a.answer_items for a in analyses.values()) / total

    print(f"  Documents: {total}")
    print(f"  Avg items/doc: {avg_items:.0f}")
    print(f"  Avg answer items/doc: {avg_ans_items:.0f}")
    print(f"  Avg answer content: {avg_ans_pct:.1f}%")

    return analyses


def step1_select_docs(analyses):
    """Select docs that have existing OCR results."""
    print("\n" + "=" * 80)
    print("STEP 1: Selecting Documents With Existing Results")
    print("=" * 80)

    import csv
    available = set()
    csv_path = RESULTS_DIR / "none" / "ocr_benchmark_per_doc.csv"
    if csv_path.exists():
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                available.add(row["doc_id"])

    selected = [d for d in sorted(analyses.keys()) if d in available]
    print(f"  {len(selected)} docs have existing OCR results (out of {len(analyses)})")

    for d in selected[:5]:
        a = analyses[d]
        pct = a.answer_chars / a.total_chars * 100 if a.total_chars else 0
        print(f"  {d} — {a.answer_items} answers, {a.answer_chars} ans_chars ({pct:.0f}%)")
    if len(selected) > 5:
        print(f"  ... and {len(selected) - 5} more")

    return selected


def step2_collect(doc_ids):
    """Collect existing OCR results."""
    print("\n" + "=" * 80)
    print("STEP 2: Collecting Existing OCR Results")
    print("=" * 80)

    results = collect(doc_ids)
    engines = sorted(set(r.engine for r in results))
    docs_covered = sorted(set(r.doc_id for r in results))

    print(f"  Found {len(results)} results across {len(engines)} engines, {len(docs_covered)} docs")
    print(f"  Engines: {', '.join(engines)}")

    engine_types = {
        "glm_ocr": "VLM", "lighton_ocr": "VLM", "paddle_vl": "VLM",
        "qwen_vl": "VLM", "chandra_ocr": "VLM", "dots_ocr": "VLM",
        "doctr": "classical", "easyocr": "classical", "surya": "classical",
        "tesseract": "classical", "rapidocr": "classical",
        "paddleocr": "classical", "onnxtr": "classical", "kerasocr": "classical",
    }
    for eng in engines:
        n = sum(1 for r in results if r.engine == eng)
        etype = engine_types.get(eng, "?")
        print(f"    {eng:15s} ({etype:10s}): {n} docs")

    return results, engine_types


def step3_compute_metrics(results):
    """Compute multi-variant CER for all results."""
    print("\n" + "=" * 80)
    print("STEP 3: Computing Multi-Variant Metrics")
    print("=" * 80)

    metrics = []
    for r in results:
        if not r.ref_text or not r.hyp_text:
            continue
        m = compute_all(r)
        metrics.append(m)

    return metrics


def step4_check_inversion(metrics, engine_types):
    """Check if rankings invert between CER_raw and CER_sorted/normalized."""
    print("\n" + "=" * 80)
    print("STEP 4: Checking Ranking Inversion")
    print("=" * 80)

    # Aggregate by engine
    engine_metrics = {}
    for m in metrics:
        if m.engine not in engine_metrics:
            engine_metrics[m.engine] = []
        engine_metrics[m.engine].append(m)

    print(f"\n  {'Engine':>15s}  {'Type':>10s}  {'CER_raw':>8s}  {'CER_norm':>8s}  "
          f"{'CER_sort':>8s}  {'TokenF1':>8s}  {'Δraw→sort':>9s}  {'N':>3s}")
    print("  " + "-" * 90)

    engine_agg = {}
    for eng in sorted(engine_metrics.keys()):
        ms = engine_metrics[eng]
        n = len(ms)
        avg_raw = statistics.mean(m.cer_raw for m in ms)
        avg_norm = statistics.mean(m.cer_normalized for m in ms)
        avg_sort = statistics.mean(m.cer_sorted for m in ms)
        avg_f1 = statistics.mean(m.token_f1 for m in ms)
        delta = avg_raw - avg_sort
        etype = engine_types.get(eng, "?")

        engine_agg[eng] = {
            "type": etype, "cer_raw": avg_raw, "cer_norm": avg_norm,
            "cer_sort": avg_sort, "token_f1": avg_f1, "delta": delta, "n": n,
        }
        print(f"  {eng:>15s}  {etype:>10s}  {avg_raw:8.4f}  {avg_norm:8.4f}  "
              f"{avg_sort:8.4f}  {avg_f1:8.4f}  {delta:+9.4f}  {n:3d}")

    # Check for inversion
    print("\n  --- Ranking Comparison ---")
    rank_raw = sorted(engine_agg.keys(), key=lambda e: engine_agg[e]["cer_raw"])
    rank_sort = sorted(engine_agg.keys(), key=lambda e: engine_agg[e]["cer_sort"])
    rank_f1 = sorted(engine_agg.keys(), key=lambda e: -engine_agg[e]["token_f1"])

    print(f"\n  {'Rank':>4s}  {'CER_raw':>15s}  {'CER_sorted':>15s}  {'Token_F1':>15s}")
    print("  " + "-" * 55)
    for i in range(max(len(rank_raw), len(rank_sort), len(rank_f1))):
        r = rank_raw[i] if i < len(rank_raw) else ""
        s = rank_sort[i] if i < len(rank_sort) else ""
        f = rank_f1[i] if i < len(rank_f1) else ""
        print(f"  {i + 1:4d}  {r:>15s}  {s:>15s}  {f:>15s}")

    # Detect inversions between classical and VLM
    inversions = []
    for i, eng_raw in enumerate(rank_raw):
        for j, eng_sort in enumerate(rank_sort):
            if eng_raw == eng_sort:
                raw_pos = i
                sort_pos = j
                if raw_pos != sort_pos:
                    t1 = engine_types.get(eng_raw, "?")
                    inversions.append((eng_raw, t1, raw_pos + 1, sort_pos + 1))

    vlm_classical_inversions = []
    for i_raw, e_raw in enumerate(rank_raw):
        for j_raw, e_other in enumerate(rank_raw):
            if i_raw >= j_raw:
                continue
            t1 = engine_types.get(e_raw, "?")
            t2 = engine_types.get(e_other, "?")
            if t1 == t2:
                continue
            # Check if order flips in sorted ranking
            i_sort = rank_sort.index(e_raw)
            j_sort = rank_sort.index(e_other)
            if (i_raw < j_raw) != (i_sort < j_sort):
                vlm_classical_inversions.append((e_raw, t1, e_other, t2))

    print(f"\n  Position changes: {len(inversions)}")
    for eng, t, rp, sp in inversions:
        direction = "↑" if sp < rp else "↓"
        print(f"    {eng} ({t}): raw #{rp} → sorted #{sp} {direction}")

    print(f"\n  Classical↔VLM inversions: {len(vlm_classical_inversions)}")
    for e1, t1, e2, t2 in vlm_classical_inversions:
        print(f"    {e1} ({t1}) vs {e2} ({t2}): order flips between CER_raw and CER_sorted")

    # Per-doc analysis for pt_train_75
    print("\n  --- Per-doc detail: pt_train_75 ---")
    for m in sorted(metrics, key=lambda x: x.cer_raw):
        if "pt_train_75" in m.doc_id:
            print(f"    {m.engine:>15s}  raw={m.cer_raw:.4f}  norm={m.cer_normalized:.4f}  "
                  f"sort={m.cer_sorted:.4f}  F1={m.token_f1:.4f}  Δ={m.cer_raw - m.cer_sorted:+.4f}")

    return engine_agg, vlm_classical_inversions, rank_raw, rank_sort


def step5_decision(engine_agg, inversions, rank_raw, rank_sort, metrics, engine_types):
    """Generate viability report."""
    print("\n" + "=" * 80)
    print("STEP 5: VIABILITY DECISION")
    print("=" * 80)

    OUT_DIR.mkdir(exist_ok=True)

    # Compute VLM vs Classical delta improvement
    vlm_deltas = [v["delta"] for e, v in engine_agg.items() if v["type"] == "VLM"]
    cls_deltas = [v["delta"] for e, v in engine_agg.items() if v["type"] == "classical"]

    avg_vlm_delta = statistics.mean(vlm_deltas) if vlm_deltas else 0
    avg_cls_delta = statistics.mean(cls_deltas) if cls_deltas else 0

    print(f"\n  Avg CER improvement (raw→sorted):")
    print(f"    VLMs:      {avg_vlm_delta:+.4f}")
    print(f"    Classical: {avg_cls_delta:+.4f}")
    print(f"    Difference: {avg_vlm_delta - avg_cls_delta:+.4f}")

    has_inversions = len(inversions) > 0
    vlm_benefits_more = avg_vlm_delta > avg_cls_delta + 0.02

    if has_inversions and vlm_benefits_more:
        decision = "GO"
        reason = (
            f"Ranking inversion confirmed: {len(inversions)} classical↔VLM pair(s) "
            f"change order. VLMs improve {avg_vlm_delta - avg_cls_delta:+.4f} more than "
            f"classical engines when format penalty is removed."
        )
    elif vlm_benefits_more:
        decision = "PARTIAL"
        reason = (
            f"No full ranking inversion, but VLMs benefit disproportionately from "
            f"format normalization (Δ={avg_vlm_delta - avg_cls_delta:+.4f}). "
            f"Finding: CER systematically underestimates VLM quality."
        )
    else:
        decision = "PIVOT"
        reason = (
            f"No significant difference. VLM delta={avg_vlm_delta:+.4f}, "
            f"classical delta={avg_cls_delta:+.4f}. "
            f"The format divergence affects both families equally."
        )

    print(f"\n  DECISION: {decision}")
    print(f"  Reason: {reason}")

    # Write detailed CSV
    csv_path = OUT_DIR / "viability_metrics.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "doc_id", "engine", "type", "cer_raw", "cer_normalized",
            "cer_sorted", "token_f1", "delta_raw_sort", "ref_len", "hyp_len",
        ])
        w.writeheader()
        for m in sorted(metrics, key=lambda x: (x.doc_id, x.engine)):
            w.writerow({
                "doc_id": m.doc_id, "engine": m.engine,
                "type": engine_types.get(m.engine, "?"),
                "cer_raw": f"{m.cer_raw:.6f}",
                "cer_normalized": f"{m.cer_normalized:.6f}",
                "cer_sorted": f"{m.cer_sorted:.6f}",
                "token_f1": f"{m.token_f1:.6f}",
                "delta_raw_sort": f"{m.cer_raw - m.cer_sorted:.6f}",
                "ref_len": m.ref_len, "hyp_len": m.hyp_len,
            })
    print(f"\n  Detailed metrics saved to {csv_path}")

    # Write report
    report_path = OUT_DIR / "VIABILITY_REPORT.md"
    report_path.write_text(_build_report(
        decision, reason, engine_agg, inversions,
        rank_raw, rank_sort, metrics, engine_types,
        avg_vlm_delta, avg_cls_delta,
    ))
    print(f"  Report saved to {report_path}")

    return decision


def _build_report(decision, reason, engine_agg, inversions,
                  rank_raw, rank_sort, metrics, engine_types,
                  avg_vlm_delta, avg_cls_delta):
    lines = [
        "# Viability Test Report: XFUND-PT Ground Truth Analysis",
        f"\n**Decision: {decision}**\n",
        f"**Reason:** {reason}\n",
        "\n## 1. Engine Comparison\n",
        f"| Engine | Type | CER_raw | CER_norm | CER_sorted | Token_F1 | Δ(raw→sort) | N |",
        f"|--------|------|---------|----------|------------|----------|-------------|---|",
    ]
    for eng in sorted(engine_agg.keys()):
        v = engine_agg[eng]
        lines.append(
            f"| {eng} | {v['type']} | {v['cer_raw']:.4f} | {v['cer_norm']:.4f} | "
            f"{v['cer_sort']:.4f} | {v['token_f1']:.4f} | {v['delta']:+.4f} | {v['n']} |"
        )

    lines.extend([
        f"\n## 2. Format Penalty by Engine Family\n",
        f"- **VLM avg improvement** (raw→sorted): {avg_vlm_delta:+.4f}",
        f"- **Classical avg improvement** (raw→sorted): {avg_cls_delta:+.4f}",
        f"- **Difference**: {avg_vlm_delta - avg_cls_delta:+.4f}",
    ])

    lines.extend([
        f"\n## 3. Rankings\n",
        f"| Rank | CER_raw | CER_sorted | Token_F1 |",
        f"|------|---------|------------|----------|",
    ])
    rank_f1 = sorted(engine_agg.keys(), key=lambda e: -engine_agg[e]["token_f1"])
    for i in range(max(len(rank_raw), len(rank_sort), len(rank_f1))):
        r = rank_raw[i] if i < len(rank_raw) else ""
        s = rank_sort[i] if i < len(rank_sort) else ""
        f = rank_f1[i] if i < len(rank_f1) else ""
        lines.append(f"| {i + 1} | {r} | {s} | {f} |")

    if inversions:
        lines.extend([
            f"\n## 4. Classical↔VLM Inversions\n",
            f"Found **{len(inversions)}** ranking inversion(s):\n",
        ])
        for e1, t1, e2, t2 in inversions:
            lines.append(f"- **{e1}** ({t1}) vs **{e2}** ({t2})")

    lines.extend([
        f"\n## 5. Key Insight\n",
        "The XFUND-PT ground truth concatenates form items in annotation order "
        "(questions and answers as separate items), producing a deconstructed text. "
        "VLMs read forms as a human would — structured, with labels inline "
        "(e.g., `Nome: Pedro C Santos`). Classical OCR engines produce fragmented "
        "text blocks closer to the GT's deconstructed format.\n",
        "Standard CER measures edit distance between these two formats, conflating "
        "**layout fidelity** with **content accuracy**. CER_sorted removes the "
        "ordering penalty, isolating content errors.\n",
    ])

    return "\n".join(lines) + "\n"


def main():
    analyses = step0_analyze_gt()
    selected = step1_select_docs(analyses)
    results, engine_types = step2_collect(selected)

    if not results:
        print("\nERROR: No OCR results found. Cannot proceed.")
        return

    metrics = step3_compute_metrics(results)
    engine_agg, inversions, rank_raw, rank_sort = step4_check_inversion(metrics, engine_types)
    decision = step5_decision(engine_agg, inversions, rank_raw, rank_sort, metrics, engine_types)

    print(f"\n{'=' * 80}")
    print(f"FINAL: {decision}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
