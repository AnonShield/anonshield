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
2. Throughput: for each calibration point, calculate (file_size_kb / processing_time) 
   after subtracting overhead, then use the MEAN across all points

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
class FileEstimate:
    """Time estimate for a specific file."""
    version: str
    strategy: str
    file_name: str
    file_path: str
    extension: str
    file_size_mb: float
    file_size_kb: float
    overhead_sec: float
    throughput_kbps: float
    estimated_time_sec: float
    estimated_time_hours: float
    calibration_source: str


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
    file_estimates: List[FileEstimate] = field(default_factory=list)


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

    Strategy (matching generate_heatmap_chart.py methodology):
    - Subtract overhead from each data point's wall time
    - Calculate throughput for each point: file_size_kb / processing_time
    - Use the MEAN of all throughput values
    - Filter out negative processing times (if overhead > wall_time)

    This approach averages the throughput across all file sizes, which is
    consistent with how the heatmap chart estimates processing time.

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

        # Calculate throughput for each point
        throughputs = []
        for p in ext_points:
            processing_time = p.wall_time_sec - overhead
            if processing_time > 0:  # Filter out negative times
                tp = p.file_size_kb / processing_time
                throughputs.append(tp)

        if throughputs:
            # Use mean throughput across all points
            avg_throughput = sum(throughputs) / len(throughputs)
            source = "mean_throughput"
            r_squared = 0.0  # Not applicable for simple averaging
        else:
            # Fallback: very conservative estimate
            avg_throughput = 0.001
            source = "fallback"
            r_squared = 0.0

        profiles[(ver, strat, ext)] = ThroughputProfile(
            version=ver,
            strategy=strat,
            extension=ext,
            overhead_sec=overhead,
            throughput_kbps=max(avg_throughput, 0.001),  # Floor to avoid div-by-zero
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
                file_estimates = []
                total_1_run = 0.0
                for f in ext_files:
                    file_time = profile.estimate_time(f.size_kb)
                    total_1_run += file_time
                    
                    file_estimates.append(FileEstimate(
                        version=version,
                        strategy=strategy,
                        file_name=f.name,
                        file_path=str(f.path),
                        extension=f.extension,
                        file_size_mb=f.size_mb,
                        file_size_kb=f.size_kb,
                        overhead_sec=profile.overhead_sec,
                        throughput_kbps=profile.throughput_kbps,
                        estimated_time_sec=file_time,
                        estimated_time_hours=file_time / 3600,
                        calibration_source=profile.source,
                    ))

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
                    file_estimates=file_estimates,
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
    lines.append("## 3. Throughput Profiles (from calibration runs)")
    lines.append("")
    lines.append("Processing rate calculated as mean(file_size_kb / (wall_time - overhead)).")
    lines.append("")
    lines.append("| Version | Strategy | Extension | Throughput (KB/s) | Source | Data Points |")
    lines.append("|---------|----------|-----------|------------------:|--------|------------:|")

    all_profile_keys = set()
    for version in ["1.0", "2.0", "3.0"]:
        for strategy in VERSION_STRATEGIES[version]:
            for ext in sorted(files_by_ext.keys()):
                if ext in VERSION_EXTENSIONS[version]:
                    all_profile_keys.add((version, strategy, ext))

    for key in sorted(all_profile_keys):
        ver, strat, ext = key
        profile = resolve_profile(profiles, overheads, ver, strat, ext)
        lines.append(f"| v{ver} | {strat} | `{ext}` | {profile.throughput_kbps:.3f} | {profile.source} | {profile.data_points} |")

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

    # ==== INDIVIDUAL FILE ESTIMATES ====
    lines.append("## 5.4 Individual File Estimates by Version & Strategy")
    lines.append("")
    lines.append("Detailed time estimates for each file, showing how file size affects processing time.")
    lines.append("")

    for version in ["1.0", "2.0", "3.0"]:
        ver_estimates = [e for e in estimates if e.version == version]
        if not ver_estimates:
            continue

        lines.append(f"### v{version}")
        lines.append("")

        strategies = VERSION_STRATEGIES[version]
        for strategy in strategies:
            strat_estimates = [e for e in ver_estimates if e.strategy == strategy]
            if not strat_estimates:
                continue

            if len(strategies) > 1:
                lines.append(f"#### Strategy: `{strategy}`")
                lines.append("")

            for ext_estimate in sorted(strat_estimates, key=lambda x: x.extension):
                lines.append(f"**Format: `{ext_estimate.extension}`** (Throughput: {ext_estimate.throughput_kbps:.3f} KB/s, Overhead: {ext_estimate.overhead_sec:.1f}s)")
                lines.append("")
                lines.append(f"| File | Size (MB) | Time (1 run) | Time ({n_runs} runs) |")
                lines.append(f"|------|----------:|-------------:|---------------:|")
                
                for fe in ext_estimate.file_estimates:
                    time_1_str = f"{fe.estimated_time_hours:.2f}h" if fe.estimated_time_hours >= 1 else f"{fe.estimated_time_sec/60:.1f}min"
                    time_n = fe.estimated_time_sec * n_runs
                    time_n_h = time_n / 3600
                    time_n_str = f"{time_n_h:.2f}h" if time_n_h >= 1 else f"{time_n/60:.1f}min"
                    lines.append(f"| {fe.file_name} | {fe.file_size_mb:.1f} | {time_1_str} | {time_n_str} |")
                
                ext_total_h = ext_estimate.estimated_time_n_runs_hours
                ext_total_str = f"{ext_total_h:.2f}h" if ext_total_h >= 1 else f"{ext_estimate.estimated_time_n_runs_sec / 60:.1f}min"
                lines.append(f"| **Total** | **{ext_estimate.total_size_mb:.1f}** | | **{ext_total_str}** |")
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
    lines.append("- For each (version, strategy, extension) observed in calibration:")
    lines.append("  - processing_time = observed_time - overhead")
    lines.append("  - throughput = file_size_kb / processing_time")
    lines.append("  - avg_throughput = mean of all throughput values")
    lines.append("- Negative processing times are filtered out")
    lines.append("- This averaging method matches the heatmap chart methodology")
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
    lines.append("- Throughput is calculated as mean across all calibration points")
    lines.append("- Small files may have proportionally higher per-file overhead")
    lines.append("  (tokenization, chunking) that isn't captured in the fixed overhead")
    lines.append("- Very large files (>100 MB) may exhibit sub-linear throughput")
    lines.append("  due to memory pressure, chunking, or I/O bottlenecks")
    lines.append("- GPU utilization may vary with batch size and file content")
    lines.append("")

    return "\n".join(lines)


def generate_before_after_comparison(
    estimates: List[Estimate],
    n_runs: int,
) -> str:
    """Generate before/after comparison report for migration scenarios."""
    lines = []
    now = datetime.now().isoformat(timespec='seconds')

    lines.append("# AnonLFI Processing Time: Before & After Comparison")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Runs per configuration:** {n_runs}")
    lines.append("")
    lines.append("This report shows the expected processing time for each file when migrating")
    lines.append("from older versions (v1.0, v2.0) to the new v3.0 with different strategies.")
    lines.append("")

    # Collect all unique files
    all_files = {}
    for e in estimates:
        for fe in e.file_estimates:
            key = (fe.file_name, fe.extension)
            if key not in all_files:
                all_files[key] = {
                    'name': fe.file_name,
                    'extension': fe.extension,
                    'size_mb': fe.file_size_mb,
                    'estimates': []
                }
            all_files[key]['estimates'].append({
                'version': fe.version,
                'strategy': fe.strategy,
                'time_hours': fe.estimated_time_hours * n_runs,
                'time_sec': fe.estimated_time_sec * n_runs,
                'throughput': fe.throughput_kbps,
            })

    # Generate comparison for each file
    for (fname, ext), fdata in sorted(all_files.items()):
        lines.append(f"## {fname}")
        lines.append("")
        lines.append(f"- **Format:** `{ext}`")
        lines.append(f"- **Size:** {fdata['size_mb']:.1f} MB")
        lines.append("")
        
        # Build comparison table
        lines.append(f"| Version | Strategy | Throughput (KB/s) | Time ({n_runs} run{'s' if n_runs > 1 else ''}) | vs v1.0 | vs v2.0 |")
        lines.append("|---------|----------|------------------:|---------------:|--------:|--------:|")
        
        # Sort: v1.0, v2.0, then v3.0 strategies
        sorted_ests = sorted(fdata['estimates'], key=lambda x: (
            {'1.0': 0, '2.0': 1, '3.0': 2}[x['version']],
            x['strategy']
        ))
        
        v1_time = None
        v2_time = None
        
        for est in sorted_ests:
            ver = est['version']
            strat = est['strategy']
            tp = est['throughput']
            time_h = est['time_hours']
            time_s = est['time_sec']
            
            # Store baseline times
            if ver == '1.0':
                v1_time = time_s
            elif ver == '2.0':
                v2_time = time_s
            
            # Format time display
            if time_h >= 1:
                time_str = f"{time_h:.2f}h"
            elif time_s >= 60:
                time_str = f"{time_s/60:.1f}min"
            else:
                time_str = f"{time_s:.1f}s"
            
            # Calculate speedups
            vs_v1 = "-"
            vs_v2 = "-"
            
            if v1_time and time_s > 0:
                speedup = v1_time / time_s
                vs_v1 = f"{speedup:.1f}x" if speedup != 1 else "baseline"
            
            if v2_time and time_s > 0 and ext == '.json':  # v1.0 doesn't support JSON
                speedup = v2_time / time_s
                vs_v2 = f"{speedup:.1f}x" if speedup != 1 else "baseline"
            
            lines.append(f"| v{ver} | {strat} | {tp:.3f} | {time_str} | {vs_v1} | {vs_v2} |")
        
        lines.append("")
        
        # Add interpretation
        if len(sorted_ests) > 1:
            v3_ests = [e for e in sorted_ests if e['version'] == '3.0']
            if v3_ests:
                fastest_v3 = min(v3_ests, key=lambda x: x['time_sec'])
                
                lines.append("**Recommendation:**")
                if ext == '.csv' and v1_time:
                    improvement = (v1_time / fastest_v3['time_sec'])
                    lines.append(f"- Migrating from v1.0 to v3.0 (`{fastest_v3['strategy']}`) provides **{improvement:.1f}x speedup**")
                    lines.append(f"- Time reduction: {v1_time/3600:.2f}h → {fastest_v3['time_sec']/3600:.2f}h (saves {(v1_time - fastest_v3['time_sec'])/3600:.2f}h)")
                elif ext == '.json' and v2_time:
                    improvement = (v2_time / fastest_v3['time_sec'])
                    lines.append(f"- Migrating from v2.0 to v3.0 (`{fastest_v3['strategy']}`) provides **{improvement:.1f}x speedup**")
                    lines.append(f"- Time reduction: {v2_time/3600:.2f}h → {fastest_v3['time_sec']/3600:.2f}h (saves {(v2_time - fastest_v3['time_sec'])/3600:.2f}h)")
                lines.append("")

    # Summary section
    lines.append("## Summary: Total Processing Time")
    lines.append("")
    lines.append(f"| Version | Strategies | Total Time ({n_runs} run{'s' if n_runs > 1 else ''}) |")
    lines.append("|---------|------------|---------------:|")
    
    for version in ["1.0", "2.0", "3.0"]:
        ver_total = sum(e.estimated_time_n_runs_hours for e in estimates if e.version == version)
        if ver_total > 0:
            ver_d = ver_total / 24
            strats = ", ".join(VERSION_STRATEGIES[version])
            lines.append(f"| v{version} | {strats} | {ver_total:.1f}h ({ver_d:.1f}d) |")
    
    grand_total = sum(e.estimated_time_n_runs_hours for e in estimates)
    grand_d = grand_total / 24
    lines.append(f"| **TOTAL** | | **{grand_total:.1f}h ({grand_d:.1f}d)** |")
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
                       help="Path to benchmark results CSV (regression/throughput data)")
    parser.add_argument("--overhead-csv", type=str, default=None,
                       help="Path to overhead calibration CSV (optional, if separate from results-csv)")
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
