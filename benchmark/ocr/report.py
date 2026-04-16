"""Report generation: terminal table, CSV, JSON, and significance matrix.

Produces the tables and figures described in METHODOLOGY.md §7:
  T1  Dataset statistics
  T2  Primary results (CER/WER/F1/ANLS with 95% CI)
  T3  Stratified results (quality tier × doc type)
  T4  Significance matrix (Wilcoxon + Cohen's d)  [requires scipy]
  T5  Error analysis — top character substitution pairs
  T6  Ablation table (if multiple preprocessing configs provided)
"""
import csv
import json
import logging
import math
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from .metrics import EngineAggregate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(v: float, digits: int = 4) -> str:
    return f"{v:.{digits}f}"


def _ci_str(mean: float, ci: tuple[float, float]) -> str:
    return f"{_fmt(mean)} [{_fmt(ci[0])}–{_fmt(ci[1])}]"


def _col_width(header: str, rows: list[str]) -> int:
    return max(len(header), *(len(r) for r in rows), 4)


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [_col_width(h, [r[i] for r in rows]) for i, h in enumerate(headers)]
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    row_fmt = "| " + " | ".join(f"{{:<{w}}}" for w in widths) + " |"
    print(sep)
    print(row_fmt.format(*headers))
    print(sep)
    for row in rows:
        print(row_fmt.format(*row))
    print(sep)


# ---------------------------------------------------------------------------
# T1 — Dataset statistics
# ---------------------------------------------------------------------------

def print_dataset_stats(results: list[dict]) -> None:
    print("\n=== T1: Dataset Statistics ===")
    from collections import Counter
    tier_count: Counter = Counter(r["quality_tier"] for r in results)
    type_count: Counter = Counter(r["doc_type"] for r in results)

    headers = ["Category", "Value", "Count"]
    rows: list[list[str]] = []
    for tier, n in sorted(tier_count.items()):
        rows.append(["quality_tier", tier, str(n)])
    for dtype, n in sorted(type_count.items()):
        rows.append(["doc_type", dtype, str(n)])
    rows.append(["total", "documents", str(len(results))])
    _print_table(headers, rows)


# ---------------------------------------------------------------------------
# T2 — Primary results
# ---------------------------------------------------------------------------

def print_primary_results(aggregates: list[EngineAggregate]) -> None:
    print("\n=== T2: Primary Results (mean [95% CI]) ===")
    headers = ["Engine", "N", "CER ↓", "WER ↓", "CER-NoDiac ↓", "Field-F1 ↑", "ANLS ↑", "Latency(s)"]
    rows = []
    for a in aggregates:
        rows.append([
            a.engine,
            str(a.n_docs),
            _ci_str(a.mean_cer, a.ci_cer),
            _ci_str(a.mean_wer, a.ci_wer),
            _fmt(a.mean_cer_no_diac),
            _fmt(a.macro_field_f1),
            _fmt(a.mean_anls),
            _fmt(a.mean_latency_s, 2),
        ])
    _print_table(headers, rows)


# ---------------------------------------------------------------------------
# T3 — Stratified results
# ---------------------------------------------------------------------------

def print_stratified_results(aggregates: list[EngineAggregate]) -> None:
    print("\n=== T3: Stratified CER (quality_tier::doc_type) ===")
    strat_keys = sorted({k for a in aggregates for k in a.stratified_cer})
    headers = ["Engine"] + strat_keys
    rows = []
    for a in aggregates:
        row = [a.engine]
        for k in strat_keys:
            v = a.stratified_cer.get(k)
            row.append(_fmt(v) if v is not None else "—")
        rows.append(row)
    _print_table(headers, rows)


# ---------------------------------------------------------------------------
# T4 — Statistical significance (Wilcoxon + Cohen's d)
# ---------------------------------------------------------------------------

def print_significance_matrix(raw_results: list[dict]) -> None:
    print("\n=== T4: Statistical Significance (Wilcoxon signed-rank, Holm-corrected) ===")
    try:
        from scipy.stats import wilcoxon
    except Exception:
        print("  [scipy unavailable — skipping significance matrix]")
        print("  Install: pip install scipy")
        return

    engines = sorted({r["engine"] for r in raw_results})
    cer_by_engine: dict[str, dict[str, float]] = {e: {} for e in engines}
    for r in raw_results:
        cer_by_engine[r["engine"]][r["doc_id"]] = r["cer"]

    pairs = [(a, b) for i, a in enumerate(engines) for b in engines[i + 1:]]
    p_values: list[tuple[str, str, float, float]] = []

    for eng_a, eng_b in pairs:
        common_docs = sorted(
            set(cer_by_engine[eng_a]) & set(cer_by_engine[eng_b])
        )
        if len(common_docs) < 10:
            continue
        diffs = [
            cer_by_engine[eng_a][d] - cer_by_engine[eng_b][d]
            for d in common_docs
        ]
        if all(x == 0 for x in diffs):
            p_values.append((eng_a, eng_b, 1.0, 0.0))
            continue
        _, p = wilcoxon(diffs, alternative="two-sided", zero_method="wilcox")

        # Cohen's d
        mean_d = sum(diffs) / len(diffs)
        std_d = math.sqrt(sum((x - mean_d) ** 2 for x in diffs) / (len(diffs) - 1))
        cohens_d = mean_d / std_d if std_d > 0 else 0.0
        p_values.append((eng_a, eng_b, p, cohens_d))

    # Holm–Bonferroni correction
    p_values.sort(key=lambda x: x[2])
    m = len(p_values)
    corrected = []
    for rank, (a, b, p, d) in enumerate(p_values):
        p_corr = min(p * (m - rank), 1.0)
        sig = "***" if p_corr < 0.001 else "**" if p_corr < 0.01 else "*" if p_corr < 0.05 else "ns"
        corrected.append([a, b, f"{p:.4f}", f"{p_corr:.4f}", sig, f"{d:.3f}"])

    headers = ["Engine A", "Engine B", "p (raw)", "p (Holm)", "Sig", "Cohen's d"]
    _print_table(headers, corrected)
    print("  Significance: *** p<0.001  ** p<0.01  * p<0.05  ns = not significant")
    print("  Cohen's d: |d|<0.2 negligible, 0.2–0.5 small, 0.5–0.8 medium, ≥0.8 large")


# ---------------------------------------------------------------------------
# T5 — Error analysis: top character substitution pairs
# ---------------------------------------------------------------------------

def print_error_analysis(raw_results: list[dict], top_n: int = 15) -> None:
    print(f"\n=== T5: Top-{top_n} Character Substitution Pairs ===")
    confusion: Counter = Counter()
    total_errors = 0

    for r in raw_results:
        ref = r.get("_ref", "")
        hyp = r.get("_hyp", "")
        if not ref or not hyp:
            continue
        pairs = _char_substitutions(ref, hyp)
        confusion.update(pairs)
        total_errors += sum(pairs.values())

    if not confusion:
        print("  [No reference texts available for error analysis]")
        print("  Re-run with store_texts=True to enable this table.")
        return

    headers = ["Rank", "GT → Pred", "Count", "% of errors"]
    rows = []
    for rank, ((gt, pred), count) in enumerate(confusion.most_common(top_n), 1):
        pct = 100 * count / total_errors if total_errors else 0
        rows.append([str(rank), f"{repr(gt)} → {repr(pred)}", str(count), f"{pct:.2f}%"])
    _print_table(headers, rows)


def _char_substitutions(ref: str, hyp: str) -> Counter:
    """Extract character-level substitution pairs via traceback of Levenshtein DP."""
    m, n = len(ref), len(hyp)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    pairs: Counter = Counter()
    i, j = m, n
    while i > 0 and j > 0:
        if ref[i - 1] == hyp[j - 1]:
            i -= 1; j -= 1
        elif dp[i][j] == dp[i - 1][j - 1] + 1:
            pairs[(ref[i - 1], hyp[j - 1])] += 1
            i -= 1; j -= 1
        elif dp[i][j] == dp[i - 1][j] + 1:
            i -= 1   # deletion
        else:
            j -= 1   # insertion
    return pairs


# ---------------------------------------------------------------------------
# Export to CSV and JSON
# ---------------------------------------------------------------------------

def export_csv(aggregates: list[EngineAggregate], raw_results: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate summary
    agg_path = out_dir / "ocr_benchmark_summary.csv"
    with agg_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "engine", "n_docs", "mean_cer", "ci_cer_lo", "ci_cer_hi",
            "mean_wer", "ci_wer_lo", "ci_wer_hi",
            "cer_no_diac", "macro_field_f1", "mean_anls", "mean_latency_s",
        ])
        for a in aggregates:
            w.writerow([
                a.engine, a.n_docs,
                a.mean_cer, a.ci_cer[0], a.ci_cer[1],
                a.mean_wer, a.ci_wer[0], a.ci_wer[1],
                a.mean_cer_no_diac, a.macro_field_f1, a.mean_anls, a.mean_latency_s,
            ])
    logger.info("Wrote %s", agg_path)

    # Per-document results
    doc_path = out_dir / "ocr_benchmark_per_doc.csv"
    if raw_results:
        keys = list(raw_results[0].keys())
        with doc_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in raw_results:
                r_flat = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()}
                w.writerow(r_flat)
        logger.info("Wrote %s", doc_path)

    # JSON
    json_path = out_dir / "ocr_benchmark_results.json"
    json_path.write_text(
        json.dumps(
            {
                "aggregates": [asdict(a) for a in aggregates],
                "per_document": raw_results,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    logger.info("Wrote %s", json_path)


# ---------------------------------------------------------------------------
# Full report (all tables)
# ---------------------------------------------------------------------------

def print_full_report(
    aggregates: list[EngineAggregate],
    raw_results: list[dict],
    *,
    out_dir: Path | None = None,
) -> None:
    print_dataset_stats(raw_results)
    print_primary_results(aggregates)
    print_stratified_results(aggregates)
    print_significance_matrix(raw_results)
    print_error_analysis(raw_results)

    if out_dir:
        export_csv(aggregates, raw_results, out_dir)
        print(f"\nResults exported to: {out_dir}")
