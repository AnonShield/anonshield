"""Consolidated ablation report.

Walks every sub-directory under ``benchmark/ocr/results/`` produced by
``run_ablation.sh`` (baseline, grayscale, binarize, deskew, clahe, denoise,
upscale, preset_scan, minimal) and builds a pivot table of
engine × preprocessing → mean CER / WER / macro-F1 / latency.

Usage:
    python -m benchmark.ocr.consolidate
    python -m benchmark.ocr.consolidate --out-csv ablation.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .report import _print_table, _fmt


RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Ordered left-to-right for the final table. Matches run_ablation.sh.
CONFIG_ORDER = [
    "baseline",
    "grayscale",
    "binarize",
    "deskew",
    "clahe",
    "denoise",
    "upscale",
    "preset_scan",
    "minimal",
]


def _load_summary(run_dir: Path) -> dict[str, dict[str, float]]:
    """Load ``ocr_benchmark_summary.csv`` as {engine: {metric: value}}."""
    summary_csv = run_dir / "ocr_benchmark_summary.csv"
    if not summary_csv.exists():
        return {}
    rows: dict[str, dict[str, float]] = {}
    with summary_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            engine = row["engine"]
            rows[engine] = {
                "mean_cer": float(row["mean_cer"]),
                "mean_wer": float(row["mean_wer"]),
                "macro_field_f1": float(row["macro_field_f1"]),
                "mean_latency_s": float(row["mean_latency_s"]),
                "n_docs": int(row["n_docs"]),
            }
    return rows


def _discover_configs(root: Path) -> list[str]:
    found = [d.name for d in root.iterdir() if d.is_dir()]
    ordered = [c for c in CONFIG_ORDER if c in found]
    extras = sorted(c for c in found if c not in CONFIG_ORDER)
    return ordered + extras


def _all_engines(data: dict[str, dict[str, dict[str, float]]]) -> list[str]:
    engines: set[str] = set()
    for per_engine in data.values():
        engines.update(per_engine.keys())
    return sorted(engines)


def _pivot(data: dict[str, dict[str, dict[str, float]]],
           metric: str) -> tuple[list[str], list[list[str]]]:
    """Return (headers, rows) for the given metric."""
    configs = list(data.keys())
    engines = _all_engines(data)
    headers = ["engine", *configs, "best", "Δ vs baseline"]
    rows: list[list[str]] = []
    for e in engines:
        vals: dict[str, float] = {}
        for cfg in configs:
            if e in data[cfg]:
                vals[cfg] = data[cfg][e][metric]
        if not vals:
            continue
        # For CER/WER/latency: lower is better. For F1: higher is better.
        higher_better = metric == "macro_field_f1"
        items = list(vals.items())
        best_cfg, _ = (max(items, key=lambda kv: kv[1])
                       if higher_better
                       else min(items, key=lambda kv: kv[1]))
        baseline_val = vals.get("baseline")
        cells = []
        for cfg in configs:
            if cfg not in vals:
                cells.append("—")
                continue
            v = vals[cfg]
            marker = "*" if cfg == best_cfg else ""
            cells.append(f"{_fmt(v)}{marker}")
        if baseline_val is not None and best_cfg != "baseline":
            delta = vals[best_cfg] - baseline_val
            sign = "+" if delta >= 0 else ""
            delta_str = f"{sign}{_fmt(delta)}"
        else:
            delta_str = "—"
        rows.append([e, *cells, best_cfg, delta_str])
    return headers, rows


def _print_metric_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    print(f"\n=== {title} ===")
    print("  (* = best per engine,  lower is better except macro-F1)")
    _print_table(headers, rows)


def build_report(root: Path = RESULTS_DIR, out_csv: Path | None = None) -> None:
    configs = _discover_configs(root)
    if not configs:
        raise SystemExit(f"No result subdirectories found in {root}")

    data: dict[str, dict[str, dict[str, float]]] = {}
    for cfg in configs:
        summary = _load_summary(root / cfg)
        if summary:
            data[cfg] = summary

    if not data:
        raise SystemExit("No benchmark summaries found — run benchmarks first.")

    print(f"Found {len(data)} configs: {', '.join(data.keys())}")
    print(f"Engines: {', '.join(_all_engines(data))}")

    for metric, title in [
        ("mean_cer", "Mean CER by engine × preprocessing"),
        ("mean_wer", "Mean WER by engine × preprocessing"),
        ("macro_field_f1", "Macro Field-F1 by engine × preprocessing"),
        ("mean_latency_s", "Mean latency (s) by engine × preprocessing"),
    ]:
        headers, rows = _pivot(data, metric)
        _print_metric_table(title, headers, rows)

    if out_csv:
        _export_csv(data, out_csv)
        print(f"\nConsolidated CSV written to: {out_csv}")


def _export_csv(data: dict[str, dict[str, dict[str, float]]], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["engine", "preprocess", "n_docs", "mean_cer", "mean_wer",
                    "macro_field_f1", "mean_latency_s"])
        for cfg, per_engine in data.items():
            for engine, metrics in per_engine.items():
                w.writerow([
                    engine, cfg, metrics["n_docs"],
                    f"{metrics['mean_cer']:.6f}",
                    f"{metrics['mean_wer']:.6f}",
                    f"{metrics['macro_field_f1']:.6f}",
                    f"{metrics['mean_latency_s']:.4f}",
                ])


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m benchmark.ocr.consolidate")
    p.add_argument("--root", type=Path, default=RESULTS_DIR,
                   help="Results root directory. Default: benchmark/ocr/results")
    p.add_argument("--out-csv", type=Path,
                   default=RESULTS_DIR / "ablation_consolidated.csv",
                   help="Output CSV path. Default: benchmark/ocr/results/ablation_consolidated.csv")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    build_report(args.root, args.out_csv)


if __name__ == "__main__":
    main()
