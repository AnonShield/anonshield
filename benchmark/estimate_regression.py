#!/usr/bin/env python3
"""
AnonLFI Benchmark Time Estimator - REGRESSION VERSION

Uses linear regression to compute throughput from calibration data.
This version fits: processing_time = a + b * file_size_kb
where throughput = 1/b KB/s

Copy of estimate.py but with regression-based throughput calculation.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Import everything from estimate.py except compute_throughput_profiles
import sys
sys.path.insert(0, str(Path(__file__).parent))
from estimate import (
    VERSION_EXTENSIONS, VERSION_STRATEGIES, EXCLUDED_EXTENSIONS,
    FileInfo, CalibrationPoint, ThroughputProfile, FileEstimate, Estimate,
    inventory_files, group_by_extension, load_calibration_data,
    compute_overhead, resolve_profile, generate_estimates,
    generate_markdown_report, generate_before_after_comparison
)


def compute_throughput_profiles_regression(
    points: List[CalibrationPoint],
    overheads: Dict[Tuple[str, str], float],
    overhead_file_pattern: str = "minimal",
) -> Dict[Tuple[str, str, str], ThroughputProfile]:
    """Compute throughput profiles using LINEAR REGRESSION.

    Strategy:
    - With 2+ data points: linear regression (processing_time = a + b*size)
      where processing_time = wall_time - overhead
      and throughput = 1/b KB/s
    - With 1 data point: use that observation

    Returns:
        Dict mapping (version, strategy, extension) -> ThroughputProfile
    """
    # Group non-overhead calibration points by (version, strategy, extension)
    grouped = defaultdict(list)
    for p in points:
        if overhead_file_pattern in p.file_name:
            continue  # Skip overhead calibration files
        key = (p.version, p.strategy, p.extension)
        grouped[key].append(p)

    profiles = {}
    for (ver, strat, ext), ext_points in grouped.items():
        overhead = overheads.get((ver, strat), 0)

        # Sort by file size descending (prefer larger files for throughput)
        ext_points.sort(key=lambda p: p.file_size_kb, reverse=True)

        if len(ext_points) >= 2:
            # Linear regression: processing_time = a + b * size_kb
            # where processing_time = wall_time - overhead
            sizes = [p.file_size_kb for p in ext_points]
            times = [p.wall_time_sec - overhead for p in ext_points]

            # Simple least squares: b = Cov(x,y) / Var(x)
            n = len(sizes)
            mean_x = sum(sizes) / n
            mean_y = sum(times) / n

            cov_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(sizes, times)) / n
            var_x = sum((x - mean_x) ** 2 for x in sizes) / n

            if var_x > 0 and cov_xy > 0:
                slope = cov_xy / var_x  # seconds per KB
                throughput = 1.0 / slope  # KB per second
                source = "regression"

                # Compute R-squared for fit quality
                a = mean_y - slope * mean_x
                ss_res = sum((y - (a + slope * x)) ** 2 for x, y in zip(sizes, times))
                ss_tot = sum((y - mean_y) ** 2 for y in times)
                r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            else:
                # Fallback: use largest file
                p = ext_points[0]
                processing_time = p.wall_time_sec - overhead
                throughput = p.file_size_kb / processing_time if processing_time > 0 else 0.0
                source = "largest_file"
                r_squared = 0.0
        else:
            # Single data point
            p = ext_points[0]
            processing_time = p.wall_time_sec - overhead
            throughput = p.file_size_kb / processing_time if processing_time > 0 else 0.0
            source = "single_point"
            r_squared = 0.0

        profiles[(ver, strat, ext)] = ThroughputProfile(
            version=ver,
            strategy=strat,
            extension=ext,
            overhead_sec=overhead,
            throughput_kbps=max(throughput, 0.001),
            source=source,
            data_points=len(ext_points),
            r_squared=r_squared,
        )

    return profiles


def main():
    parser = argparse.ArgumentParser(
        description="AnonLFI Benchmark Time Estimator (REGRESSION version)"
    )
    parser.add_argument("--data-dir", type=str, default="dados_teste",
                       help="Directory containing test files")
    parser.add_argument("--runs", type=int, default=10,
                       help="Number of runs to estimate for (default: 10)")
    parser.add_argument("--results-csv", type=str, default="benchmark/results/benchmark_results.csv",
                       help="Path to benchmark results CSV (regression/throughput data)")
    parser.add_argument("--overhead-csv", type=str, default=None,
                       help="Path to overhead calibration CSV (optional, if separate from results-csv)")
    parser.add_argument("--output", type=str, default="benchmark/ESTIMATES_regression.md",
                       help="Output Markdown file path")
    parser.add_argument("--overhead-pattern", type=str, default="minimal",
                       help="Filename pattern to identify overhead calibration runs")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    csv_path = Path(args.results_csv)

    # 1. Inventory test files
    print(f"[INFO] Inventorying files in: {data_dir}")
    files = inventory_files(data_dir)
    files_by_ext = group_by_extension(files)

    print(f"[INFO] Found {len(files)} files across {len(files_by_ext)} formats")
    for ext in sorted(files_by_ext.keys()):
        count = len(files_by_ext[ext])
        size_mb = sum(f.size_mb for f in files_by_ext[ext])
        print(f"  {ext:>6}: {count:>4} files, {size_mb:>8.1f} MB")

    # 2. Load all calibration data
    print(f"\n[INFO] Loading calibration data from: {csv_path}")
    cal_points = load_calibration_data(csv_path)
    print(f"[INFO] Loaded {len(cal_points)} successful calibration points")

    # Load overhead data separately if specified
    overhead_csv = Path(args.overhead_csv) if args.overhead_csv else csv_path
    if args.overhead_csv:
        print(f"\n[INFO] Loading overhead calibration from: {overhead_csv}")
        overhead_points = load_calibration_data(overhead_csv)
        print(f"[INFO] Loaded {len(overhead_points)} overhead calibration points")
    else:
        overhead_points = cal_points

    # 3. Compute overhead from minimal file runs
    print(f"\n[INFO] Computing model loading overhead (pattern: '{args.overhead_pattern}')...")
    overheads = compute_overhead(overhead_points, args.overhead_pattern)

    if not overheads:
        print("[WARN] No overhead calibration data found!")
        # Provide heuristic defaults
        for version, strategies in VERSION_STRATEGIES.items():
            for strategy in strategies:
                overheads[(version, strategy)] = 90.0

    for (ver, strat), overhead in sorted(overheads.items()):
        print(f"  v{ver} | {strat:>10} | overhead = {overhead:.1f}s")

    # 4. Compute throughput profiles using REGRESSION
    print(f"\n[INFO] Computing throughput profiles (REGRESSION method)...")
    profiles = compute_throughput_profiles_regression(cal_points, overheads, args.overhead_pattern)

    for key in sorted(profiles.keys()):
        p = profiles[key]
        r2_str = f"R²={p.r_squared:.3f}" if p.r_squared > 0 else ""
        print(f"  v{p.version} | {p.strategy:>10} | {p.extension:>6} | "
              f"{p.throughput_kbps:.3f} KB/s | {p.data_points} pts {r2_str}")

    # 5. Generate estimates
    print(f"\n[INFO] Generating estimates for {args.runs} runs...")
    estimates = generate_estimates(files_by_ext, profiles, overheads, args.runs)

    # 6. Generate and save report
    report = generate_markdown_report(
        files, files_by_ext, estimates, overheads, profiles,
        args.runs, args.data_dir
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"\n[INFO] Report saved to: {output_path}")

    # 7. Generate before/after comparison report
    comparison_report = generate_before_after_comparison(estimates, args.runs)
    comparison_path = output_path.parent / (output_path.stem + "_comparison.md")
    with open(comparison_path, 'w') as f:
        f.write(comparison_report)
    
    print(f"[INFO] Comparison report saved to: {comparison_path}")

    # Print summary to terminal
    grand_total_h = sum(e.estimated_time_n_runs_hours for e in estimates)
    grand_total_d = grand_total_h / 24

    print(f"\n{'='*60}")
    print(f"ESTIMATE SUMMARY ({args.runs} runs) - REGRESSION METHOD")
    print(f"{'='*60}")
    for version in ["1.0", "2.0", "3.0"]:
        ver_h = sum(e.estimated_time_n_runs_hours for e in estimates if e.version == version)
        ver_d = ver_h / 24
        strats = ", ".join(VERSION_STRATEGIES[version])
        print(f"  v{version} ({strats}): {ver_h:.1f}h ({ver_d:.1f}d)")
    print(f"  {'='*50}")
    print(f"  TOTAL: {grand_total_h:.1f}h ({grand_total_d:.1f}d)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
