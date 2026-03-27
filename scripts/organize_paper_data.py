#!/usr/bin/env python3
"""
organize_paper_data.py
======================
Organizes benchmark results and datasets for the paper, performing:

1. Removes 6 buggy scan targets from D1 (vulnnet_scans_openvas) and D1C (benchmark/converted_datasets)
2. Creates paper_data/ directory structure with clean copies of all result CSVs
3. Copies D2/D3 dataset files and configs
4. Verifies data count expectations
5. Generates a summary verification report

BUGGY files to remove (D1 and D1C):
  Duplicates (with "(1)" in name):
    - openvas_sonarqube_6 (1).7
    - openvas_mongo_3 (1).4
    - openvas_gitlab_gitlab-ce_10.0.0-ce (1).0
    - openvas_elasticsearch_5 (1).6
  Empty scans:
    - openvas_owasp_railsgoat
    - openvas_infosecwarrior_dns-lab_v2
"""

import csv
import os
import shutil
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
BASE = Path("/media/kapelinski/8402F7AD02F7A27A/Users/crist/Documents/anonshield/tool")
OUT  = BASE / "paper_data"

D1_DIR   = BASE / "vulnnet_scans_openvas"
D1C_BASE = BASE / "benchmark" / "converted_datasets"
D1C_FMTS = ["docx", "json", "xlsx", "pdf_images"]

# Buggy directory names (basenames inside D1_DIR and D1C_BASE/<fmt>/)
BUGGY_DIRS = [
    "openvas_sonarqube_6 (1).7",
    "openvas_mongo_3 (1).4",
    "openvas_gitlab_gitlab-ce_10.0.0-ce (1).0",
    "openvas_elasticsearch_5 (1).6",
    "openvas_owasp_railsgoat",
    "openvas_infosecwarrior_dns-lab_v2",
]

# String patterns that mark a row as coming from a buggy file
BUGGY_PATTERNS = ["(1)", "railsgoat", "dns-lab_v2", "dns-lab_v"]

# Source result CSVs →  (destination subpath inside paper_data/benchmark_results/, label)
RESULT_SOURCES = {
    # D1 + D1C
    "D1_D1C/d1_openvas_all_strategies": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/04_full_single_file_1run/benchmark_results.csv",
        "D1 OpenVAS – all formats, all versions, all strategies (1 run)",
    ),
    "D1_D1C/d1c_converted_all_strategies": (
        BASE / "benchmark/orchestrated_results/converted/benchmark_results.csv",
        "D1C Converted formats – all versions, all strategies (1 run)",
    ),
    "D1_D1C/regression_3runs": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/03_regression_3runs/benchmark_results.csv",
        "Regression test – 3 runs (D1 subset)",
    ),
    # D2 – CAIS/RNP       (default config, session_20260208_005447)
    "D2_default_config/ctciber_csv_10runs": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/01_ctciber_csv_cache200k/benchmark_results.csv",
        "D2 CSV – AnonShield all strategies, 10 runs (default config)",
    ),
    "D2_default_config/ctciber_json_10runs": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/02_ctciber_json_cache200k/benchmark_results.csv",
        "D2 JSON – AnonShield all strategies, 10 runs (default config)",
    ),
    # D2 – CAIS/RNP       (anonymization_config.json, session_ctciber_cve)
    "D2_anon_config/ctciber_csv_10runs": (
        BASE / "benchmark/orchestrated_results/session_ctciber_cve_20260214_031239/01_ctciber_csv_cache200k/benchmark_results.csv",
        "D2 CSV – AnonShield all strategies, 10 runs (anonymization_config.json)",
    ),
    "D2_anon_config/ctciber_json_10runs": (
        BASE / "benchmark/orchestrated_results/session_ctciber_cve_20260214_031239/02_ctciber_json_cache200k/benchmark_results.csv",
        "D2 JSON – AnonShield all strategies, 10 runs (anonymization_config.json)",
    ),
    # D2 – extra (session_20260211 – direct consolidated files)
    "D2_extra/consolidated_json_10runs": (
        BASE / "ignore/dados_CTCiber_AnonShield/benchmark_results/session_20260211_220041/01_consolidated_json_10runs/benchmark_results.csv",
        "D2 Consolidated JSON – AnonShield, 10 runs",
    ),
    "D2_extra/consolidated_csv_10runs": (
        BASE / "ignore/dados_CTCiber_AnonShield/benchmark_results/session_20260211_220041/02_consolidated_csv_10runs/benchmark_results.csv",
        "D2 Consolidated CSV – AnonShield, 10 runs",
    ),
    # D3 – Mock CAIS/CVE   (default config, session_20260208_005447)
    "D3_default_config/cve_csv_10runs": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/00_cve_dataset_v3_10runs_csv/benchmark_results.csv",
        "D3 CVE CSV – AnonShield all strategies, 10 runs (default config)",
    ),
    "D3_default_config/cve_json_10runs": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/01_cve_dataset_v3_10runs_json/benchmark_results.csv",
        "D3 CVE JSON – AnonShield all strategies, 10 runs (default config)",
    ),
    "D3_default_config/cve_csv_default_strat": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/03_cve_csv_default/benchmark_results.csv",
        "D3 CVE CSV – AnonShield default strategy only, 10 runs",
    ),
    "D3_default_config/cve_json_default_strat": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/04_cve_json_default/benchmark_results.csv",
        "D3 CVE JSON – AnonShield default strategy only, 10 runs",
    ),
    # D3 – Mock CAIS/CVE   (anonymization_config_cve.json, session_ctciber_cve)
    "D3_anon_config/cve_csv_10runs": (
        BASE / "benchmark/orchestrated_results/session_ctciber_cve_20260214_031239/03_cve_csv_default/benchmark_results.csv",
        "D3 CVE CSV – AnonShield all strategies, 10 runs (anonymization_config_cve.json)",
    ),
    "D3_anon_config/cve_json_10runs": (
        BASE / "benchmark/orchestrated_results/session_ctciber_cve_20260214_031239/04_cve_json_default/benchmark_results.csv",
        "D3 CVE JSON – AnonShield all strategies, 10 runs (anonymization_config_cve.json)",
    ),
    # Combined session results
    "combined/session_20260208_005447": (
        BASE / "benchmark/orchestrated_results/session_20260208_005447/combined_results.csv",
        "Combined all runs – session_20260208_005447",
    ),
    "combined/session_ctciber_cve_20260214": (
        BASE / "benchmark/orchestrated_results/session_ctciber_cve_20260214_031239/combined_results.csv",
        "Combined D2+D3 with anon config – session_ctciber_cve_20260214_031239",
    ),
}

# D2 / D3 raw data files and configs
DATASET_FILES = {
    "D2_cais_original": [
        BASE / "ignore/dados_CTCiber_AnonShield/consolidated_data.csv",
        BASE / "ignore/dados_CTCiber_AnonShield/consolidated_data.json",
        BASE / "anonymization_config.json",
    ],
    "D3_mock_cais": [
        BASE / "cve_dataset_anonimizados_stratified.csv",
        BASE / "cve_dataset_anonimizados_stratified.json",
        BASE / "anonymization_config_cve.json",
    ],
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def is_buggy_row(row: dict) -> bool:
    fname = row.get("file_name", "")
    fpath = row.get("file_path", "")
    return any(p in fname or p in fpath for p in BUGGY_PATTERNS)


def clean_csv(src: Path, dst: Path) -> tuple[int, int]:
    """Copy src→dst removing rows from buggy files. Returns (total, removed)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    total = removed = 0
    with open(src, newline="", encoding="utf-8") as fin, \
         open(dst, "w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            total += 1
            if is_buggy_row(row):
                removed += 1
            else:
                writer.writerow(row)
    return total, removed


def remove_buggy_dirs(base_dir: Path, label: str, dry_run: bool = False) -> list[str]:
    """Remove the BUGGY_DIRS from base_dir. Returns list of removed dirs."""
    removed = []
    for bad in BUGGY_DIRS:
        target = base_dir / bad
        if target.exists():
            if not dry_run:
                shutil.rmtree(target)
            removed.append(str(target.relative_to(BASE)))
            print(f"  {'[DRY] ' if dry_run else ''}REMOVED  {label}/{bad}")
        else:
            print(f"  SKIP (not found): {label}/{bad}")
    return removed


def csv_stats(path: Path) -> dict:
    """Return basic stats dict for a CSV."""
    if not path.exists():
        return {"error": "file not found"}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return {"rows": 0}
    versions = Counter(r.get("version", "?") for r in rows)
    strategies = Counter(r.get("strategy", "?") for r in rows)
    extensions = Counter(r.get("file_extension", "?") for r in rows)
    statuses = Counter(r.get("status", "?") for r in rows)
    unique_files = len({r.get("file_name", "") for r in rows})
    return {
        "rows": len(rows),
        "unique_files": unique_files,
        "versions": dict(versions),
        "strategies": dict(strategies),
        "extensions": dict(extensions),
        "statuses": dict(statuses),
    }


# ─── STEP 1: Remove buggy dirs from D1 ───────────────────────────────────────

def step1_remove_buggy_d1():
    print("\n" + "=" * 70)
    print("STEP 1 – Remove buggy directories from D1 (vulnnet_scans_openvas)")
    print("=" * 70)
    removed = remove_buggy_dirs(D1_DIR, "vulnnet_scans_openvas")
    print(f"  Total removed from D1: {len(removed)}")
    return removed


# ─── STEP 2: Remove buggy dirs from D1C ──────────────────────────────────────

def step2_remove_buggy_d1c():
    print("\n" + "=" * 70)
    print("STEP 2 – Remove buggy directories from D1C (benchmark/converted_datasets)")
    print("=" * 70)
    all_removed = []
    for fmt in D1C_FMTS:
        fmt_dir = D1C_BASE / fmt
        if fmt_dir.exists():
            removed = remove_buggy_dirs(fmt_dir, f"converted_datasets/{fmt}")
            all_removed.extend(removed)
        else:
            print(f"  WARNING: {fmt_dir} not found")
    print(f"  Total removed from D1C: {len(all_removed)}")
    return all_removed


# ─── STEP 3: Build paper_data/ structure ─────────────────────────────────────

def step3_create_structure():
    print("\n" + "=" * 70)
    print("STEP 3 – Creating paper_data/ directory structure")
    print("=" * 70)

    # Create top-level README
    OUT.mkdir(exist_ok=True)
    report_lines = []
    report_lines.append("# Paper Data – AnonShield Benchmark")
    report_lines.append(f"\nGenerated: {datetime.now().isoformat()}")
    report_lines.append("""
## Structure

```
paper_data/
├── README.md                    ← this file
├── configs/                     ← anonymization config files
├── datasets/
│   ├── D2_cais_original/        ← D2 raw data (private, cannot be released)
│   └── D3_mock_cais/            ← D3 synthetic public data
├── benchmark_results/
│   ├── D1_D1C/                  ← OpenVAS (D1) + converted formats (D1C) results
│   ├── D2_default_config/       ← D2 CAIS results, default config
│   ├── D2_anon_config/          ← D2 CAIS results, anonymization_config.json
│   ├── D2_extra/                ← D2 extra consolidated runs
│   ├── D3_default_config/       ← D3 Mock CVE results, default config
│   ├── D3_anon_config/          ← D3 Mock CVE results, anonymization_config_cve.json
│   └── combined/                ← Combined session result CSVs
└── analysis/                    ← Generated charts and analysis from analisys1
```

## Datasets

| ID  | Source       | Format     | Files | Access  |
|-----|-------------|------------|-------|---------|
| D1  | OpenVAS (VulnLab) | CSV, TXT, PDF, XML | 129 clean | Public |
| D1C | Converted from D1 | XLSX, DOCX, JSON, PDF(img) | 129 clean | Public |
| D2  | Tenable (CAIS/RNP) | CSV, JSON | 1 consolidated | Private |
| D3  | Synthetic (Mock CAIS) | CSV, JSON | 1 synthetic | Public |

**Note:** 7 scan targets were removed from D1/D1C as buggy:
- Duplicates (name contains " (1)"): sonarqube_6, mongo_3, gitlab_gitlab-ce_10.0.0-ce, elasticsearch_5
- Empty scans: owasp_railsgoat, infosecwarrior_dns-lab_v2
""")
    report_lines.append("\n## Benchmark Results Summary\n")

    # ── Configs ──
    cfg_dir = OUT / "configs"
    cfg_dir.mkdir(exist_ok=True)
    for src in [BASE / "anonymization_config.json", BASE / "anonymization_config_cve.json"]:
        if src.exists():
            shutil.copy2(src, cfg_dir / src.name)
            print(f"  Copied config: {src.name}")

    # ── Dataset files ──
    for ds, files in DATASET_FILES.items():
        ds_dir = OUT / "datasets" / ds
        ds_dir.mkdir(parents=True, exist_ok=True)
        for src in files:
            if src.exists():
                shutil.copy2(src, ds_dir / src.name)
                size_mb = src.stat().st_size / 1_048_576
                print(f"  Copied dataset [{ds}]: {src.name}  ({size_mb:.2f} MB)")
            else:
                print(f"  WARNING: dataset file not found: {src}")

    # ── Benchmark result CSVs (cleaned) ──
    results_dir = OUT / "benchmark_results"
    clean_stats = {}
    for dest_subpath, (src_path, label) in RESULT_SOURCES.items():
        if not src_path.exists():
            print(f"  WARNING: result CSV not found: {src_path}")
            continue
        dst = results_dir / dest_subpath / "benchmark_results_clean.csv"
        total, removed = clean_csv(src_path, dst)
        print(f"  Cleaned [{dest_subpath}]: {total} rows → {total - removed} kept, {removed} buggy removed")
        stats = csv_stats(dst)
        clean_stats[dest_subpath] = {"label": label, "src": str(src_path), "stats": stats, "removed": removed}
        report_lines.append(f"### {dest_subpath}\n_{label}_\n")
        report_lines.append(f"- Rows (clean): {stats['rows']}  (removed: {removed})")
        report_lines.append(f"- Unique files: {stats.get('unique_files', '?')}")
        report_lines.append(f"- Versions: {stats.get('versions', {})}")
        report_lines.append(f"- Strategies: {stats.get('strategies', {})}")
        report_lines.append(f"- Extensions: {stats.get('extensions', {})}")
        report_lines.append(f"- Statuses: {stats.get('statuses', {})}\n")

    # ── Analysis charts ──
    analysis_src = BASE / "benchmark/orchestrated_results/analisys1"
    analysis_dst = OUT / "analysis"
    if analysis_src.exists():
        shutil.copytree(analysis_src, analysis_dst, dirs_exist_ok=True)
        count = sum(1 for _ in analysis_dst.rglob("*") if _.is_file())
        print(f"  Copied analysis charts: {count} files → paper_data/analysis/")

    # Write README
    readme_path = OUT / "README.md"
    readme_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n  Written: {readme_path}")

    return clean_stats


# ─── STEP 4: Verify D1/D1C counts ────────────────────────────────────────────

def step4_verify_counts(clean_stats: dict):
    print("\n" + "=" * 70)
    print("STEP 4 – Verifying D1/D1C data counts")
    print("=" * 70)

    # D1 verification:
    #   129 targets × 4 formats = 516 unique files
    #   per version & strategy, 1 run each
    TARGET_D1 = 129
    D1_EXTS = 4

    d1_path = OUT / "benchmark_results/D1_D1C/d1_openvas_all_strategies/benchmark_results_clean.csv"
    if d1_path.exists():
        with open(d1_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # Group by version+strategy+extension
        combo = defaultdict(set)
        ext_per_vs = defaultdict(Counter)
        for row in rows:
            key = (row["version"], row["strategy"])
            combo[key].add(row["file_name"])
            ext_per_vs[key][row["file_extension"]] += 1

        print(f"\n  D1 Clean rows: {len(rows)}")
        print(f"  Expected unique files per (version, strategy): {TARGET_D1 * D1_EXTS} (129 targets × 4 exts)")
        print(f"\n  Breakdown by version × strategy:")
        for (v, s), fnames in sorted(combo.items()):
            exts = Counter(f.rsplit(".", 1)[-1] for f in fnames)
            flag = "✓" if len(fnames) == TARGET_D1 * D1_EXTS else "✗ MISMATCH"
            print(f"    v{v} / {s:<12}  files={len(fnames):4d}  {flag}  {dict(ext_per_vs[(v,s)])}")

    # D1C verification:
    d1c_path = OUT / "benchmark_results/D1_D1C/d1c_converted_all_strategies/benchmark_results_clean.csv"
    if d1c_path.exists():
        with open(d1c_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        combo = defaultdict(set)
        for row in rows:
            key = (row["version"], row["strategy"])
            combo[key].add(row["file_name"])

        print(f"\n  D1C Clean rows: {len(rows)}")
        print(f"  D1C formats: docx, json, xlsx, pdf_images (4 formats)")
        print(f"  Expected files per (version, strategy): {TARGET_D1 * 4} (129 targets × 4 fmts)")
        print(f"\n  Breakdown by version × strategy:")
        for (v, s), fnames in sorted(combo.items()):
            flag = "✓" if len(fnames) == TARGET_D1 * 4 else f"✗ ({len(fnames)}≠{TARGET_D1*4})"
            print(f"    v{v} / {s:<12}  files={len(fnames):4d}  {flag}")

    # D1 dir count check
    if D1_DIR.exists():
        d1_dirs = [d for d in D1_DIR.iterdir() if d.is_dir()]
        print(f"\n  D1 scan dirs remaining: {len(d1_dirs)}  (expected 129 after removing 7 from 136)")
        if len(d1_dirs) == 129:
            print("  ✓ D1 directory count correct")
        else:
            print(f"  ✗ Expected 129 but got {len(d1_dirs)}")

    # D1C dir count check
    for fmt in D1C_FMTS:
        fmt_dir = D1C_BASE / fmt
        if fmt_dir.exists():
            dirs = [d for d in fmt_dir.iterdir() if d.is_dir()]
            flag = "✓" if len(dirs) == 129 else f"✗ (got {len(dirs)})"
            print(f"  D1C/{fmt} dirs: {len(dirs)}  {flag}")


# ─── STEP 5: Write JSON summary ───────────────────────────────────────────────

def step5_write_summary(clean_stats: dict, d1_removed: list, d1c_removed: list):
    print("\n" + "=" * 70)
    print("STEP 5 – Writing verification summary")
    print("=" * 70)

    summary = {
        "generated": datetime.now().isoformat(),
        "buggy_targets_removed": BUGGY_DIRS,
        "d1_dirs_deleted": d1_removed,
        "d1c_dirs_deleted": d1c_removed,
        "result_csvs": {
            k: {
                "label": v["label"],
                "source": v["src"],
                "rows_clean": v["stats"].get("rows", 0),
                "rows_removed_buggy": v["removed"],
                "unique_files": v["stats"].get("unique_files", 0),
                "versions": v["stats"].get("versions", {}),
                "strategies": v["stats"].get("strategies", {}),
                "extensions": v["stats"].get("extensions", {}),
                "statuses": v["stats"].get("statuses", {}),
            }
            for k, v in clean_stats.items()
        },
    }

    out_path = OUT / "verification_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {out_path}")
    return summary


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print(f"paper_data organizer – {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"BASE: {BASE}")
    print(f"OUT:  {OUT}")

    d1_removed  = step1_remove_buggy_d1()
    d1c_removed = step2_remove_buggy_d1c()
    clean_stats = step3_create_structure()
    step4_verify_counts(clean_stats)
    step5_write_summary(clean_stats, d1_removed, d1c_removed)

    print("\n" + "=" * 70)
    print("DONE – paper_data/ is ready.")
    print(f"  {OUT}")
    print("=" * 70)


if __name__ == "__main__":
    main()
