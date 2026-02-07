#!/usr/bin/env python3
"""
AnonLFI Benchmark Time Estimator

Uses a two-component model to estimate benchmark execution time:

    estimated_time = overhead + (file_size_kb / throughput_kbps)

Where:
- overhead   = fixed model loading + startup cost per run (measured from minimal file runs)
- throughput = processing rate in KB/s for each (version, strategy, format) combination

Calibration sources:
1. Overhead: benchmark runs against a near-zero content file (benchmark/overhead_calibration/)
2. Throughput: derived from smoke test runs by subtracting overhead from observed time

Usage:
    python benchmark/estimate.py [--data-dir path] [--runs N] [--results-csv path]
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


# =============================================================================
# CONFIGURATION (mirrors benchmark.py)
# =============================================================================

VERSION_EXTENSIONS = {
    "1.0": {".txt", ".docx", ".csv", ".xlsx", ".xml"},
    "2.0": {".txt", ".pdf", ".docx", ".csv", ".xlsx", ".xml", ".json",
            ".jpeg", ".jpg", ".png", ".gif", ".bmp", ".tiff"},
    "3.0": {".txt", ".log", ".pdf", ".docx", ".csv", ".xlsx", ".xml",
            ".json", ".jsonl",
            ".jpeg", ".jpg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".jp2", ".pnm"},
}

VERSION_STRATEGIES = {
    "1.0": ["default"],
    "2.0": ["default"],
    "3.0": ["presidio", "fast", "balanced"],
}

EXCLUDED_EXTENSIONS = {".anonymous", ".anon", ".bak", ".tmp"}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FileInfo:
    """Information about a test file."""
    path: Path
    name: str
    extension: str
    size_bytes: int
    size_kb: float
    size_mb: float


@dataclass
class CalibrationPoint:
    """Observed processing time for a specific version/strategy/file."""
    version: str
    strategy: str
    file_name: str
    extension: str
    file_size_kb: float
    wall_time_sec: float
    status: str


@dataclass
class ThroughputProfile:
    """Processing profile for a (version, strategy, extension) combination."""
    version: str
    strategy: str
    extension: str
    overhead_sec: float           # Fixed model loading cost
    throughput_kbps: float        # Processing rate in KB/s (content only, after overhead)
    source: str                   # How this profile was derived
    data_points: int              # Number of calibration points used
    r_squared: float = 0.0       # Fit quality (if computed from regression)

    def estimate_time(self, file_size_kb: float) -> float:
        """Estimate processing time for a file of given size."""
        if self.throughput_kbps <= 0:
            return self.overhead_sec
        return self.overhead_sec + (file_size_kb / self.throughput_kbps)


@dataclass
class Estimate:
    """Time estimate for a specific (version, strategy, extension) combination."""
    version: str
    strategy: str
    extension: str
    file_count: int
    total_size_mb: float
    overhead_sec: float
    throughput_kbps: float
    estimated_time_1_run_sec: float
    estimated_time_n_runs_sec: float
    estimated_time_n_runs_hours: float
    calibration_source: str


# =============================================================================
# INVENTORY
# =============================================================================

def inventory_files(data_dir: Path) -> List[FileInfo]:
    """Build complete inventory of all test files."""
    files = []
    for f in data_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() not in EXCLUDED_EXTENSIONS:
            size = f.stat().st_size
            files.append(FileInfo(
                path=f,
                name=f.name,
                extension=f.suffix.lower(),
                size_bytes=size,
                size_kb=size / 1024,
                size_mb=size / (1024 * 1024),
            ))
    return sorted(files, key=lambda x: (x.extension, x.name))


def group_by_extension(files: List[FileInfo]) -> Dict[str, List[FileInfo]]:
    """Group files by extension."""
    groups = defaultdict(list)
    for f in files:
        groups[f.extension].append(f)
    return dict(groups)


# =============================================================================
# CALIBRATION
# =============================================================================

def load_calibration_data(csv_path: Path) -> List[CalibrationPoint]:
    """Load calibration data from benchmark results CSV."""
    points = []

    if not csv_path.exists():
        print(f"  [WARN] Results CSV not found: {csv_path}")
        return points

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return points

        for row in reader:
            try:
                status = row.get('status', '')
                if status != "SUCCESS":
                    continue
                points.append(CalibrationPoint(
                    version=row.get('version', ''),
                    strategy=row.get('strategy', ''),
                    file_name=row.get('file_name', ''),
                    extension=row.get('file_extension', ''),
                    file_size_kb=float(row.get('file_size_kb', 0)),
                    wall_time_sec=float(row.get('wall_clock_time_sec', 0)),
                    status=status,
                ))
            except (ValueError, KeyError):
                continue

    return points


def compute_overhead(
    points: List[CalibrationPoint],
    overhead_file_pattern: str = "minimal",
) -> Dict[Tuple[str, str], float]:
    """Compute model loading overhead per (version, strategy) from minimal file runs.

    Returns:
        Dict mapping (version, strategy) -> avg overhead in seconds
    """
    overhead_points = defaultdict(list)

    for p in points:
        if overhead_file_pattern in p.file_name:
            key = (p.version, p.strategy)
            overhead_points[key].append(p.wall_time_sec)

    overheads = {}
    for key, times in overhead_points.items():
        overheads[key] = sum(times) / len(times)

    return overheads


def compute_throughput_profiles(
    points: List[CalibrationPoint],
    overheads: Dict[Tuple[str, str], float],
    overhead_file_pattern: str = "minimal",
) -> Dict[Tuple[str, str, str], ThroughputProfile]:
    """Compute throughput profiles from calibration data.

    Strategy:
    - With 2+ data points of different sizes: linear regression (time = a + b*size)
      to separate per-file overhead from content-proportional processing.
    - With 1 data point: use the single observation, preferring the largest file
      available since larger files give better signal-to-noise for throughput.

    The key insight: small files (~5 KB) have significant per-file processing
    overhead (tokenization, chunking) that makes their apparent throughput
    artificially low. Using the largest available file minimizes this bias.

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
            # Two-point (or more) linear regression: time = a + b * size_kb
            # where a captures per-file overhead and 1/b is throughput
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
            # Single data point: compute throughput from this observation
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
            throughput_kbps=max(throughput, 0.001),  # Floor to avoid div-by-zero
            source=source,
            data_points=len(ext_points),
            r_squared=r_squared,
        )

    return profiles


def resolve_profile(
    profiles: Dict[Tuple[str, str, str], ThroughputProfile],
    overheads: Dict[Tuple[str, str], float],
    version: str,
    strategy: str,
    extension: str,
) -> ThroughputProfile:
    """Look up or derive a throughput profile with fallback chain.

    Priority:
    1. Direct match: (version, strategy, extension)
    2. Same version, different strategy (closest match)
    3. Different version, same extension
    4. Heuristic fallback
    """
    # Direct match
    key = (version, strategy, extension)
    if key in profiles:
        return profiles[key]

    # Fallback 1: same version, different strategy
    for s in VERSION_STRATEGIES.get(version, []):
        fallback_key = (version, s, extension)
        if fallback_key in profiles:
            p = profiles[fallback_key]
            overhead = overheads.get((version, strategy), p.overhead_sec)
            return ThroughputProfile(
                version=version, strategy=strategy, extension=extension,
                overhead_sec=overhead,
                throughput_kbps=p.throughput_kbps,
                source=f"extrapolated_from_{s}",
                data_points=p.data_points,
            )

    # Fallback 2: different version, same extension
    for v in ["3.0", "2.0", "1.0"]:
        if v == version:
            continue
        for s in VERSION_STRATEGIES.get(v, []):
            fallback_key = (v, s, extension)
            if fallback_key in profiles:
                p = profiles[fallback_key]
                overhead = overheads.get((version, strategy), p.overhead_sec)
                return ThroughputProfile(
                    version=version, strategy=strategy, extension=extension,
                    overhead_sec=overhead,
                    throughput_kbps=p.throughput_kbps,
                    source=f"extrapolated_from_v{v}_{s}",
                    data_points=p.data_points,
                )

    # Fallback 3: heuristic (conservative)
    overhead = overheads.get((version, strategy), 90.0)  # Default ~90s
    return ThroughputProfile(
        version=version, strategy=strategy, extension=extension,
        overhead_sec=overhead,
        throughput_kbps=0.5,  # Very conservative: 0.5 KB/s
        source="heuristic",
        data_points=0,
    )


# =============================================================================
# ESTIMATION ENGINE
# =============================================================================

def generate_estimates(
    files_by_ext: Dict[str, List[FileInfo]],
    profiles: Dict[Tuple[str, str, str], ThroughputProfile],
    overheads: Dict[Tuple[str, str], float],
    n_runs: int,
) -> List[Estimate]:
    """Generate time estimates for all combinations using throughput model."""
    estimates = []

    for version, strategies in VERSION_STRATEGIES.items():
        supported_exts = VERSION_EXTENSIONS[version]

        for strategy in strategies:
            for ext, ext_files in files_by_ext.items():
                if ext not in supported_exts:
                    continue

                # Get or derive throughput profile
                profile = resolve_profile(profiles, overheads, version, strategy, ext)

                total_size_mb = sum(f.size_mb for f in ext_files)

                # Estimate each file individually based on its size
                total_1_run = 0.0
                for f in ext_files:
                    total_1_run += profile.estimate_time(f.size_kb)

                total_n_runs = total_1_run * n_runs

                estimates.append(Estimate(
                    version=version,
                    strategy=strategy,
                    extension=ext,
                    file_count=len(ext_files),
                    total_size_mb=total_size_mb,
                    overhead_sec=profile.overhead_sec,
                    throughput_kbps=profile.throughput_kbps,
                    estimated_time_1_run_sec=total_1_run,
                    estimated_time_n_runs_sec=total_n_runs,
                    estimated_time_n_runs_hours=total_n_runs / 3600,
                    calibration_source=profile.source,
                ))

    return estimates


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_markdown_report(
    files: List[FileInfo],
    files_by_ext: Dict[str, List[FileInfo]],
    estimates: List[Estimate],
    overheads: Dict[Tuple[str, str], float],
    profiles: Dict[Tuple[str, str, str], ThroughputProfile],
    n_runs: int,
    data_dir: str,
) -> str:
    """Generate detailed Markdown report."""
    lines = []
    now = datetime.now().isoformat(timespec='seconds')

    lines.append("# AnonLFI Benchmark Time Estimates")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Data directory:** `{data_dir}`")
    lines.append(f"**Planned runs per configuration:** {n_runs}")
    lines.append("")

    # ==== ESTIMATION MODEL ====
    lines.append("## Estimation Model")
    lines.append("")
    lines.append("```")
    lines.append("estimated_time = overhead + (file_size_kb / throughput_kbps)")
    lines.append("```")
    lines.append("")
    lines.append("- **overhead**: Fixed cost per run (model loading, interpreter startup)")
    lines.append("- **throughput_kbps**: Processing rate in KB/s for the given format")
    lines.append("- Each file is estimated individually based on its actual size")
    lines.append("")

    # ==== FILE INVENTORY ====
    lines.append("## 1. File Inventory")
    lines.append("")
    lines.append("| Extension | Count | Total Size | Avg Size | Largest File |")
    lines.append("|-----------|------:|-----------:|---------:|:-------------|")

    total_files = 0
    total_size_mb = 0

    for ext in sorted(files_by_ext.keys()):
        ext_files = files_by_ext[ext]
        count = len(ext_files)
        total_mb = sum(f.size_mb for f in ext_files)
        avg_kb = sum(f.size_kb for f in ext_files) / count if count > 0 else 0
        largest = max(ext_files, key=lambda x: x.size_bytes)
        largest_str = f"{largest.name} ({largest.size_mb:.1f} MB)"

        lines.append(f"| `{ext}` | {count} | {total_mb:.1f} MB | {avg_kb:.1f} KB | {largest_str} |")
        total_files += count
        total_size_mb += total_mb

    lines.append(f"| **Total** | **{total_files}** | **{total_size_mb:.1f} MB** | | |")
    lines.append("")

    # ==== OVERHEAD CALIBRATION ====
    lines.append("## 2. Model Loading Overhead (from calibration runs)")
    lines.append("")
    lines.append("Measured by running a near-zero content file (5 bytes) to isolate")
    lines.append("model loading and interpreter startup cost from content processing.")
    lines.append("")
    lines.append("| Version | Strategy | Overhead (s) | Runs |")
    lines.append("|---------|----------|-------------:|-----:|")

    for (ver, strat), overhead in sorted(overheads.items()):
        lines.append(f"| v{ver} | {strat} | {overhead:.1f} | 3 |")

    lines.append("")

    # ==== THROUGHPUT PROFILES ====
    lines.append("## 3. Throughput Profiles (from smoke test)")
    lines.append("")
    lines.append("Processing rate after subtracting model loading overhead.")
    lines.append("")
    lines.append("| Version | Strategy | Extension | Throughput (KB/s) | Source | Data Points | R^2 |")
    lines.append("|---------|----------|-----------|------------------:|--------|------------:|----:|")

    all_profile_keys = set()
    for version in ["1.0", "2.0", "3.0"]:
        for strategy in VERSION_STRATEGIES[version]:
            for ext in sorted(files_by_ext.keys()):
                if ext in VERSION_EXTENSIONS[version]:
                    all_profile_keys.add((version, strategy, ext))

    for key in sorted(all_profile_keys):
        ver, strat, ext = key
        profile = resolve_profile(profiles, overheads, ver, strat, ext)
        r2_str = f"{profile.r_squared:.3f}" if profile.r_squared > 0 else "-"
        lines.append(f"| v{ver} | {strat} | `{ext}` | {profile.throughput_kbps:.3f} | {profile.source} | {profile.data_points} | {r2_str} |")

    lines.append("")

    # ==== VERSION SUPPORT MATRIX ====
    lines.append("## 4. Version Support Matrix")
    lines.append("")
    lines.append("| Extension | v1.0 | v2.0 | v3.0 |")
    lines.append("|-----------|:----:|:----:|:----:|")

    all_exts = sorted(set().union(*VERSION_EXTENSIONS.values()))
    for ext in all_exts:
        if ext in files_by_ext:
            v1 = "Y" if ext in VERSION_EXTENSIONS["1.0"] else "-"
            v2 = "Y" if ext in VERSION_EXTENSIONS["2.0"] else "-"
            v3 = "Y" if ext in VERSION_EXTENSIONS["3.0"] else "-"
            lines.append(f"| `{ext}` | {v1} | {v2} | {v3} |")

    lines.append("")

    # ==== DETAILED ESTIMATES BY VERSION ====
    for version in ["1.0", "2.0", "3.0"]:
        ver_estimates = [e for e in estimates if e.version == version]
        if not ver_estimates:
            continue

        strategies = VERSION_STRATEGIES[version]
        lines.append(f"## 5.{version.replace('.', '')} Estimates for v{version}")
        lines.append("")

        for strategy in strategies:
            strat_estimates = [e for e in ver_estimates if e.strategy == strategy]
            if not strat_estimates:
                continue

            if strategy != "default":
                lines.append(f"### Strategy: `{strategy}`")
            lines.append("")
            lines.append(f"| Extension | Files | Total Size | Overhead | Throughput | 1 Run | {n_runs} Runs | Source |")
            lines.append(f"|-----------|------:|-----------:|---------:|-----------:|------:|-------:|--------|")

            strat_total_sec = 0
            for e in sorted(strat_estimates, key=lambda x: x.extension):
                strat_total_sec += e.estimated_time_n_runs_sec
                one_run_h = e.estimated_time_1_run_sec / 3600
                n_run_h = e.estimated_time_n_runs_hours
                lines.append(
                    f"| `{e.extension}` | {e.file_count} | {e.total_size_mb:.1f} MB | "
                    f"{e.overhead_sec:.1f}s | {e.throughput_kbps:.3f} KB/s | "
                    f"{one_run_h:.1f}h | {n_run_h:.1f}h | {e.calibration_source} |"
                )

            strat_total_h = strat_total_sec / 3600
            strat_total_d = strat_total_h / 24
            lines.append(f"| **Subtotal** | | | | | | **{strat_total_h:.1f}h ({strat_total_d:.1f}d)** | |")
            lines.append("")

        ver_total_h = sum(e.estimated_time_n_runs_hours for e in ver_estimates)
        ver_total_d = ver_total_h / 24
        lines.append(f"**v{version} Total: {ver_total_h:.1f} hours ({ver_total_d:.1f} days)**")
        lines.append("")

    # ==== GRAND TOTAL ====
    lines.append("## 6. Grand Total")
    lines.append("")

    grand_total_h = sum(e.estimated_time_n_runs_hours for e in estimates)
    grand_total_d = grand_total_h / 24

    lines.append("| Version | Strategies | Estimated Time |")
    lines.append("|---------|------------|---------------:|")

    for version in ["1.0", "2.0", "3.0"]:
        ver_h = sum(e.estimated_time_n_runs_hours for e in estimates if e.version == version)
        ver_d = ver_h / 24
        strats = ", ".join(VERSION_STRATEGIES[version])
        lines.append(f"| v{version} | {strats} | {ver_h:.1f}h ({ver_d:.1f}d) |")

    lines.append(f"| **TOTAL** | | **{grand_total_h:.1f}h ({grand_total_d:.1f}d)** |")
    lines.append("")

    # ==== METHODOLOGY ====
    lines.append("## 7. Methodology")
    lines.append("")
    lines.append("### Two-Component Model")
    lines.append("Each file's processing time is estimated as:")
    lines.append("")
    lines.append("```")
    lines.append("time = overhead + (file_size_kb / throughput_kbps)")
    lines.append("```")
    lines.append("")
    lines.append("This separates the fixed cost (model loading, interpreter startup,")
    lines.append("library imports) from the variable cost (proportional to file size).")
    lines.append("")
    lines.append("### Overhead Calibration")
    lines.append("- A near-zero content file (5 bytes) is processed 3 times per")
    lines.append("  version/strategy combination")
    lines.append("- The average wall clock time is used as the overhead constant")
    lines.append("- This represents: Python startup + model loading + NLP pipeline init")
    lines.append("")
    lines.append("### Throughput Derivation")
    lines.append("- For each (version, strategy, extension) observed in smoke tests:")
    lines.append("  - processing_time = observed_time - overhead")
    lines.append("  - throughput = file_size_kb / processing_time")
    lines.append("- Multiple data points are averaged to reduce noise")
    lines.append("- When direct observations are unavailable, throughput is")
    lines.append("  extrapolated from similar combinations (same version/different")
    lines.append("  strategy, or same extension/different version)")
    lines.append("")
    lines.append("### Per-File Estimation")
    lines.append("- Each file in the dataset is estimated individually based on")
    lines.append("  its actual size, not an average")
    lines.append("- This correctly handles datasets with extreme size variance")
    lines.append("  (e.g., 1 KB files alongside 250 MB files)")
    lines.append("")
    lines.append("### Assumptions")
    lines.append("- Sequential execution (one file at a time)")
    lines.append("- Model cache is warm (models already downloaded)")
    lines.append("- No system resource contention")
    lines.append("- Linear throughput scaling (may underestimate for very large files")
    lines.append("  where memory pressure causes swapping)")
    lines.append("")
    lines.append("### Limitations")
    lines.append("- Throughput is derived from small smoke test files (<400 KB)")
    lines.append("- Very large files (>100 MB) may exhibit sub-linear throughput")
    lines.append("  due to memory pressure, chunking, or I/O bottlenecks")
    lines.append("- GPU utilization may vary with batch size and file content")
    lines.append("- Overhead may vary slightly by format due to format-specific")
    lines.append("  processor initialization")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="AnonLFI Benchmark Time Estimator (throughput-based model)"
    )
    parser.add_argument("--data-dir", type=str, default="dados_teste",
                       help="Directory containing test files")
    parser.add_argument("--runs", type=int, default=10,
                       help="Number of runs to estimate for (default: 10)")
    parser.add_argument("--results-csv", type=str, default="benchmark/results/benchmark_results.csv",
                       help="Path to benchmark results CSV (smoke test + overhead calibration)")
    parser.add_argument("--output", type=str, default="benchmark/ESTIMATES.md",
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

    # 3. Compute overhead from minimal file runs
    print(f"\n[INFO] Computing model loading overhead (pattern: '{args.overhead_pattern}')...")
    overheads = compute_overhead(cal_points, args.overhead_pattern)

    if not overheads:
        print("[WARN] No overhead calibration data found!")
        print("[WARN] Run: python3 benchmark/benchmark.py --benchmark --data-dir benchmark/overhead_calibration/data --runs 3")
        print("[WARN] Using heuristic overhead estimates (90s)")
        # Provide heuristic defaults
        for version, strategies in VERSION_STRATEGIES.items():
            for strategy in strategies:
                overheads[(version, strategy)] = 90.0

    for (ver, strat), overhead in sorted(overheads.items()):
        print(f"  v{ver} | {strat:>10} | overhead = {overhead:.1f}s")

    # 4. Compute throughput profiles
    print(f"\n[INFO] Computing throughput profiles...")
    profiles = compute_throughput_profiles(cal_points, overheads, args.overhead_pattern)

    for key in sorted(profiles.keys()):
        p = profiles[key]
        print(f"  v{p.version} | {p.strategy:>10} | {p.extension:>6} | "
              f"{p.throughput_kbps:.3f} KB/s | {p.data_points} points")

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

    # Print summary to terminal
    grand_total_h = sum(e.estimated_time_n_runs_hours for e in estimates)
    grand_total_d = grand_total_h / 24

    print(f"\n{'='*60}")
    print(f"ESTIMATE SUMMARY ({args.runs} runs)")
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
