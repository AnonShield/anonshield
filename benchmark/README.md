# AnonLFI Benchmark Suite

A professional, modular benchmarking framework for evaluating and comparing
AnonLFI anonymization tool versions (1.0, 2.0, and 3.0). Designed for
reproducible academic research with comprehensive metrics collection,
fault tolerance, and incremental progress persistence.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Setup Phase](#setup-phase)
- [Running Benchmarks](#running-benchmarks)
- [Smoke Test](#smoke-test)
- [Time Estimation](#time-estimation)
- [Overhead Calibration](#overhead-calibration)
- [Regression Estimation](#regression-estimation)
- [CLI Reference](#cli-reference)
- [Metrics Reference](#metrics-reference)
- [File Format Support Matrix](#file-format-support-matrix)
- [Directory Structure](#directory-structure)
- [Resume and Fault Tolerance](#resume-and-fault-tolerance)
- [Output Files](#output-files)
- [Methodology](#methodology)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)

---

## Overview

The benchmark suite measures anonymization performance across three AnonLFI
versions with varying strategies, collecting time, memory, CPU, GPU, I/O, and
throughput metrics. It is designed for multi-day benchmark campaigns with full
resilience to interruptions.

**Versions under test:**

| Version | Strategies | Input Modes | Secret Key |
|---------|------------|-------------|:----------:|
| v1.0    | default    | Single file only | No |
| v2.0    | default    | Single file or directory | Yes |
| v3.0    | presidio, fast, balanced, slm | Single file or directory | Yes |

**Key capabilities:**

- Automatic virtual environment creation via `uv sync`
- GPU-aware setup for v3.0 (CUDA 12.8, following production Dockerfile)
- Model cache warming before benchmarks begin
- Real-time terminal output streaming during processing
- Per-run log file persistence
- Incremental state saving (resume from any interruption)
- Comprehensive metrics: wall clock, CPU, memory, GPU, I/O, throughput
- CSV and JSON result export

---

## Architecture

The benchmark suite follows a modular, SOLID-principled design:

```
benchmark.py
├── Configuration Layer
│   ├── AnonVersion          # Enum: V1_0, V2_0, V3_0
│   ├── Strategy             # Enum: DEFAULT, PRESIDIO, FAST, BALANCED, SLM
│   └── VersionConfig        # Per-version paths, extensions, capabilities
│
├── Data Layer
│   ├── BenchmarkMetrics     # 40+ field dataclass for all metrics
│   └── RunState             # Persistent state for resume support
│
├── Setup Layer
│   └── EnvironmentSetup     # venv creation, deps, torch config, cache warming
│
├── Collection Layer
│   ├── MetricsParser        # Parses /usr/bin/time -v output via regex
│   ├── FileMetricsCollector # File size, line count, character count
│   ├── GpuSample            # GPU utilization, VRAM, temperature snapshot
│   ├── _query_nvidia_smi()  # nvidia-smi subprocess interface
│   └── ProcessMonitor       # Background thread sampling CPU, memory, GPU
│
├── Execution Layer
│   └── BenchmarkRunner      # Command building, process execution, monitoring
│
├── Persistence Layer
│   └── ResultsManager       # CSV append, JSON export, state management
│
└── Orchestration Layer
    └── BenchmarkOrchestrator  # CLI handling, phase coordination
```

### Execution Flow

1. **Setup phase** (`--setup`): For each version, create a virtual environment
   using `uv sync`, configure PyTorch (GPU or CPU), and run a warmup
   anonymization to download and cache NLP models.

2. **Benchmark phase** (`--benchmark`): For each (version, strategy, file, run)
   combination, execute the anonymization wrapped in `/usr/bin/time -v` while
   a background `ProcessMonitor` thread samples CPU, memory, and GPU metrics
   at 500ms intervals. Results are appended to CSV after each run and state
   is persisted to JSON for resume capability.

---

## Prerequisites

- **OS:** Linux (tested on Ubuntu/WSL2)
- **Python:** 3.10+
- **uv:** Package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **psutil:** `pip install psutil` (in your base Python)
- **GNU time:** `/usr/bin/time` (not the shell builtin; install with `apt install time`)
- **nvidia-smi:** Required for GPU metrics (optional; gracefully degrades if unavailable)
- **CUDA 12.x:** Required for v3.0 GPU mode (optional; `--cpu-only` flag available)

### Installing uv on Ubuntu/WSL

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Verify:
~/.local/bin/uv --version
```

The benchmark script searches for `uv` in `PATH`, `~/.local/bin/`, `~/.cargo/bin/`,
and `/usr/local/bin/`.

---

## Quick Start

```bash
# Navigate to the project root (parent of anonlfi_1.0/, anonlfi_2.0/, benchmark/)
cd /path/to/anonshield/tool

# 1. Run smoke test (setup + quick benchmark with minimal data)
python benchmark/benchmark.py --smoke-test

# 2. Run full benchmark with production data (10 runs)
python benchmark/benchmark.py --setup
python benchmark/benchmark.py --benchmark --data-dir ./dados_teste --runs 10 --continue-on-error
```

---

## Setup Phase

The setup phase creates isolated virtual environments for each version and
prepares them for benchmarking.

```bash
# Setup all versions (GPU mode for v3.0)
python benchmark/benchmark.py --setup

# Setup with CPU-only PyTorch for v3.0
python benchmark/benchmark.py --setup --cpu-only

# Force-recreate all environments
python benchmark/benchmark.py --setup --force-setup

# Setup specific versions only
python benchmark/benchmark.py --setup --versions 1.0 3.0
```

### What Setup Does

For each version:

1. **`uv sync`**: Creates a virtual environment and installs all dependencies
   from the version's `pyproject.toml`. The `UV_PROJECT_ENVIRONMENT` variable
   controls the venv location (`.venv` for v1.0/v2.0, `.venv_benchmark` for v3.0
   to avoid conflicting with the development venv).

2. **PyTorch configuration** (v3.0 only): Installs GPU-enabled PyTorch from
   `https://download.pytorch.org/whl/cu128` and `cupy-cuda12x==12.3.0`,
   following the same logic as the production GPU Dockerfile. Falls back to
   CPU-only if GPU installation fails.

3. **Model cache warmup**: Runs a minimal anonymization
   (`"O analista João Silva está em Porto Alegre. Email: joao@example.com"`)
   to trigger model downloads (xlm-roberta-large, spaCy pt_core_news_lg, etc.).
   This prevents model download time from contaminating benchmark measurements.

### Virtual Environment Locations

| Version | Venv Path | Working Directory |
|---------|-----------|-------------------|
| v1.0 | `anonlfi_1.0/.venv/` | `anonlfi_1.0/` |
| v2.0 | `anonlfi_2.0/.venv/` | `anonlfi_2.0/` |
| v3.0 | `.venv_benchmark/` | `.` (project root) |

---

## Running Benchmarks

```bash
# Basic benchmark with default smoke test data
python benchmark/benchmark.py --benchmark

# Full benchmark with production data, 10 runs each
python benchmark/benchmark.py --benchmark --data-dir ./dados_teste --runs 10

# Benchmark specific versions
python benchmark/benchmark.py --benchmark --versions 2.0 3.0 --data-dir ./dados_teste

# Filter files by regex pattern
python benchmark/benchmark.py --benchmark --data-dir ./dados_teste --file-pattern "openvas.*\.xml"

# Suppress real-time output (faster, less verbose)
python benchmark/benchmark.py --benchmark --no-show-output --data-dir ./dados_teste

# Continue even if individual runs fail
python benchmark/benchmark.py --benchmark --continue-on-error --data-dir ./dados_teste

# Clean all previous results before starting
python benchmark/benchmark.py --benchmark --clean --data-dir ./dados_teste
```

### What Happens During a Benchmark Run

For each `(version, strategy, file, run_number)` combination:

1. Check if this run was already completed (resume support) -- skip if so.
2. Verify the file extension is supported by this version -- mark SKIPPED if not.
3. Collect file metrics (size, line count, character count).
4. Build the anonymization command with appropriate arguments.
5. Execute wrapped in `/usr/bin/time -v`, streaming output to terminal and log file.
6. A `ProcessMonitor` thread samples CPU, memory, and GPU every 500ms.
7. Parse `/usr/bin/time -v` output for OS-level metrics.
8. Compute derived metrics (throughput, memory efficiency).
9. Append results to CSV immediately; update persistent state.

### Command Construction

The benchmark builds version-specific commands:

- **v1.0:** `python anon.py <absolute_file_path>`
  - No strategy flag, no secret key, single file only
- **v2.0:** `python anon.py <absolute_file_path>`
  - `ANON_SECRET_KEY` set in environment
- **v3.0:** `python anon.py <absolute_file_path> --anonymization-strategy <strategy> --output-dir <path> --overwrite --use-datasets --batch-size auto`
  - `ANON_SECRET_KEY` set in environment
  - `--overwrite` ensures re-runs don't fail on existing output files
  - `--use-datasets` and `--batch-size auto` for GPU optimization (presidio/fast/balanced only)
  - SLM strategy uses Ollama instead of Presidio — `--use-datasets` and `--batch-size` are not added

All file paths are resolved to absolute paths since each version executes from
its own working directory.

---

## Smoke Test

The smoke test is a quick validation that all versions are correctly set up
and can process files:

```bash
python benchmark/benchmark.py --smoke-test
```

This is equivalent to:
```bash
python benchmark/benchmark.py --setup --benchmark --runs 1 \
    --data-dir benchmark/smoke_test_data/dados_teste
```

### Smoke Test Data

Located in `benchmark/smoke_test_data/dados_teste/`:

```
dados_teste/
├── cve_dataset_mock_cais_stratified.csv   (37 KB)
├── cve_dataset_mock_cais_stratified.json  (11 KB)
├── teste-exemplo-artigo.txt               (1 KB)
└── vulnnet_scans_openvas/
    └── vulnnet_scans_openvas/
        ├── openvas_alpine_3.7/
        │   ├── openvas_alpine_3.7.csv
        │   ├── openvas_alpine_3.7.pdf
        │   ├── openvas_alpine_3.7.txt
        │   └── openvas_alpine_3.7.xml
        ├── exemplo.docx
        └── exemplo.xlsx
```

**Expected smoke test results:**

| Version | Strategy | Expected | Notes |
|---------|----------|----------|-------|
| v1.0 | default | 7 SUCCESS, 2 SKIPPED | .json and .pdf not supported |
| v2.0 | default | 9 SUCCESS | All formats supported |
| v3.0 | presidio | 9 SUCCESS | All formats, all strategies |
| v3.0 | fast | 9 SUCCESS | May report 0 entities (by design) |
| v3.0 | balanced | 9 SUCCESS | All formats |
| v3.0 | slm | 9 SUCCESS | Uses Ollama (local LLM), requires Ollama running |

> **Note on v3.0 fast strategy:** The fast strategy uses xlm-roberta directly
> and may report 0 detected entities. This is expected behavior -- it counts
> entities from `merged_entities` which may be empty if the transformer
> detects nothing. This does not affect anonymization quality metrics.

---

## Time Estimation

Before committing to a multi-day benchmark campaign, use the estimation tool
to project total runtime:

```bash
# Default: estimate for 10 runs using full dados_teste directory
python benchmark/estimate.py

# Custom parameters
python benchmark/estimate.py --data-dir ./dados_teste --runs 10 \
    --results-csv benchmark/results/benchmark_results.csv \
    --output benchmark/ESTIMATES.md
```

### How Estimates Work

1. **Inventory:** Scans the data directory and catalogs all files by extension and size.
2. **Calibration:** Loads observed per-file processing times from smoke test CSV results.
3. **Extrapolation:** For each (version, strategy, extension) combination:
   - Uses observed time if directly available from calibration data.
   - Falls back to same version/different strategy, then cross-version estimates.
   - Applies sub-linear scaling (0.7x size ratio) for files larger than 10 MB.
4. **Report:** Generates a detailed Markdown report broken down by version,
   strategy, and file format.

The output is saved to `benchmark/ESTIMATES.md`.

---

## Overhead Calibration

Measures the fixed model-loading cost per version/strategy by processing a
near-zero content file (5 bytes), isolating interpreter startup + NLP model
initialization from actual text processing.

```bash
# Calibrate all versions/strategies, 10 runs each
python3 benchmark/benchmark.py --calibrate-overhead --runs 10

# Calibrate specific version only
python3 benchmark/benchmark.py --calibrate-overhead --versions 3.0 --runs 5
```

Results are saved to `benchmark_results.csv` with
`measurement_mode='overhead_calibration'`.

### Measured Overheads (10-run calibration, 2026-02-06)

| Version | Strategy | Mean (s) | Std (s) | Min (s) | Max (s) | Memory (MB) |
|---------|----------|:--------:|:-------:|:-------:|:-------:|:-----------:|
| v1.0    | default  |  54.81   |  0.66   |  53.77  |  55.96  |   2,467     |
| v2.0    | default  |  58.32   |  2.87   |  55.07  |  62.95  |   2,467     |
| v3.0    | presidio |  58.70   |  0.78   |  57.63  |  60.12  |   3,121     |
| v3.0    | fast     |  57.80   |  0.93   |  56.35  |  59.59  |   3,121     |
| v3.0    | balanced |  62.27   |  6.03   |  55.43  |  72.50  |   3,121     |

Overhead is dominated by NLP model loading (xlm-roberta-large, spaCy
pt_core_news_lg). The cost is paid once per process invocation regardless
of input size.

---

## Regression Estimation

For files too large to benchmark directly (e.g., 248 MB CSV, 445 MB JSON),
the `--regression` flag estimates total processing time by:

1. Creating subsets of the source file at multiple sizes (e.g., 0.25, 0.5, 1, 2 MB)
2. Benchmarking each subset N times (for statistical robustness)
3. Fitting a linear model: **time = intercept + slope x size_kb**
4. Extrapolating to the full file size

### Quick Start

```bash
# Estimate processing time for a large CSV (default sizes: 0.25, 0.5, 1, 2 MB)
python3 benchmark/benchmark.py --regression \
    --regression-source cve_dataset_mock_cais_stratified.csv \
    --versions 1.0 --runs 3

# Estimate for both CSV and JSON, v2.0 only
python3 benchmark/benchmark.py --regression \
    --regression-source cve_dataset_mock_cais_stratified.csv,cve_dataset_mock_cais_stratified.json \
    --versions 2.0 --runs 3

# Custom subset sizes (256 KB to 4 MB) and specific target size
python3 benchmark/benchmark.py --regression \
    --regression-source data.csv \
    --regression-sizes 0.25,0.5,1,2,4 \
    --regression-target 500 \
    --versions 3.0 --runs 5
```

### How It Works

**Step 1: Subset Creation**

For CSV files, the tool copies the header row plus data rows until the
target byte size is reached. For JSON arrays, it serializes elements
one-by-one until the target size is met. Subsets are created in
`benchmark/regression_subsets/` and cleaned up after the run.

**Step 2: Benchmarking**

Each subset is processed through the standard `BenchmarkRunner` pipeline
(single-file mode with `/usr/bin/time -v` and process monitoring). The
`--runs` parameter controls how many times each subset size is benchmarked.

**Step 3: Linear Regression**

The tool performs ordinary least squares (OLS) regression on the data
points `(file_size_kb, mean_wall_clock_time_sec)`:

```
time = intercept + slope * size_kb

where:
  intercept ~ model loading overhead (seconds)
  slope     ~ per-KB processing rate (seconds/KB)
  1/slope   ~ throughput (KB/s)
```

With only 2 data points the fit is exact (R^2 = 1.0). With 3+ points,
R^2 indicates goodness of fit. Values > 0.95 confirm linear scaling.

**Step 4: Prediction**

The model extrapolates to the target file size. By default this is the
source file size, but `--regression-target` can override it.

### Interpreting Results

The output includes two analysis sections:

**1. Time Regression Table**

| Column | Meaning |
|--------|---------|
| Config | version and strategy (e.g., v1.0\|default) |
| Pts | number of (size, time) data points used |
| Intercept(s) | fixed overhead per invocation in seconds |
| Slope(s/KB) | seconds per KB of input data |
| R^2 | coefficient of determination (1.0 = perfect linear fit) |
| Predicted(s) | estimated wall-clock time for the target file size |
| Duration | human-readable prediction |

**2. Resource Scaling Analysis**

For each version/strategy, a table shows how resource consumption changes
with input size:

| Metric | What it tells you |
|--------|-------------------|
| Peak RSS (MB) | Process memory -- constant means models dominate, linear means input is buffered |
| User Time (s) | CPU processing time -- should scale linearly with input |
| System Time (s) | Kernel time (I/O, syscalls) -- typically sublinear |
| CPU % | Multi-core utilization (>100% = multi-threaded) -- usually constant |
| GPU Util % | GPU compute load -- usually constant (fixed batch size) |
| GPU VRAM (MB) | GPU memory -- usually constant (model weights dominate) |
| FS Writes | Output I/O -- should scale linearly (output proportional to input) |

Each metric is classified as: **constant** (<5% elasticity), **sublinear**
(5-30%), **~linear** (30-80%), **linear** (80-120%), or **superlinear** (>120%).

### Practical Considerations

- **Subset sizes matter.** Use sizes that are large enough to dominate the
  overhead but small enough to run in reasonable time. Default `0.25,0.5,1,2`
  MB works well for most datasets. For extremely dense data (e.g., CSV with
  large text fields), even 1 MB can take 7+ minutes per run.

- **Minimum 2 sizes required.** Linear regression needs at least 2 data
  points. Using 3-4 sizes provides validation of the linear assumption.

- **3 runs recommended.** Multiple runs per size smooth out variance from
  system load, garbage collection, and I/O caching.

- **Linearity assumption.** The model assumes processing time scales linearly
  with file size. This holds well for text-heavy formats (CSV, JSON, TXT, XML)
  but may underestimate for formats with non-linear parsing costs (PDF, images).

- **Extrapolation risk.** Predictions far beyond the largest measured size
  carry uncertainty. Memory pressure, swapping, and chunking behavior may cause
  super-linear scaling for very large files. Monitor `max_resident_set_kb` for
  signs of memory pressure.

- **State management.** Regression runs are saved with `measurement_mode='regression'`
  and support resume via `--continue-on-error`. If interrupted, re-running the
  same command will skip already-completed runs.

### Example: v1.0 CSV Regression Results (2026-02-06)

Source: `cve_dataset_mock_cais_stratified.csv` (247.5 MB), 3 runs per size.

**Raw Data:**

| Size (MB) | Run 1 (s) | Run 2 (s) | Run 3 (s) | Mean (s) | Std (s) | Throughput (KB/s) |
|:---------:|:---------:|:---------:|:---------:|:--------:|:-------:|:-----------------:|
| 1.0       | 431.95    | 431.57    | 414.78    | 426.10   | 9.81    | 2.40              |
| 2.0       | 784.36    | 805.42    | 810.13    | 799.97   | 13.72   | 2.56              |

**Regression Model:**

```
time = 52.87 + 0.365327 * size_kb
  Intercept: 52.87s  (cf. calibrated overhead: 54.81s)
  Slope:     0.365327 s/KB = 2.74 KB/s throughput
  R^2:       1.0000 (2 points, exact fit)
```

**Predictions:**

| Target Size | Predicted Time | Duration |
|:-----------:|:--------------:|:--------:|
| 4 MB        | 1,549 s        | 25m 49s  |
| 16 MB       | 6,038 s        | 1h 41m   |
| 64 MB       | 23,995 s       | 6h 40m   |
| 247.5 MB    | 92,641 s       | 25h 44m  |

The intercept (52.87s) closely matches the independently calibrated
overhead (54.81s), validating the two-component model.

---

## CLI Reference

```
python benchmark/benchmark.py [OPTIONS]
```

### Mode Selection

| Flag | Description |
|------|-------------|
| `--setup` | Run environment setup (create venvs, install deps, warm cache) |
| `--benchmark` | Run benchmarks (single-file or directory mode) |
| `--smoke-test` | Quick validation (setup + 1-run benchmark with minimal data) |
| `--calibrate-overhead` | Measure model loading overhead per version/strategy using a 5-byte file |
| `--regression` | Estimate processing time for large files via linear regression on subsets |

At least one mode must be specified. Modes can be combined:
`--setup --benchmark`.

### Setup Options

| Flag | Default | Description |
|------|---------|-------------|
| `--force-setup` | false | Force recreation of virtual environments |
| `--gpu` | true | Use GPU-enabled PyTorch for v3.0 |
| `--cpu-only` | false | Use CPU-only PyTorch (overrides `--gpu`) |

### Benchmark Options

| Flag | Default | Description |
|------|---------|-------------|
| `--data-dir PATH` | `benchmark/smoke_test_data/dados_teste` | Directory containing test files |
| `--versions V [V...]` | all | Versions to benchmark (choices: 1.0, 2.0, 3.0) |
| `--runs N` | 3 | Number of runs per configuration |
| `--file PATH [PATH...]` | none | Direct file path(s) to benchmark (no directory scanning) |
| `--file-pattern REGEX` | none | Regex pattern to filter test files |
| `--results-dir PATH` | `benchmark/results` | Custom results directory (isolated state/CSV/JSON) |
| `--secret-key KEY` | `benchmark-secret-key-2026` | Secret key for ANON_SECRET_KEY |
| `--directory-mode` | false | Process all files in a single invocation (v2.0/v3.0 only) |

### Regression Options (use with `--regression`)

| Flag | Default | Description |
|------|---------|-------------|
| `--regression-source PATHS` | *required* | Comma-separated paths to source CSV/JSON files |
| `--regression-sizes SIZES` | `0.25,0.5,1,2` | Comma-separated subset sizes in MB |
| `--regression-target MB` | auto | Target size in MB for prediction (default: source file size) |

### Output Options

| Flag | Default | Description |
|------|---------|-------------|
| `--show-output` | true | Stream real-time output from anon.py to terminal |
| `--no-show-output` | false | Suppress real-time output |
| `--verbose`, `-v` | false | Verbose logging |

### Error Handling

| Flag | Default | Description |
|------|---------|-------------|
| `--continue-on-error` | false | Continue benchmarking even if individual runs fail |

### State Management

| Flag | Default | Description |
|------|---------|-------------|
| `--clean` | false | Delete all previous results and state before running |

---

## Metrics Reference

Each benchmark run collects the following metrics, exported as columns in the
CSV and JSON result files.

### Identification Fields

| Metric | Type | Description |
|--------|------|-------------|
| `version` | str | AnonLFI version (1.0, 2.0, 3.0) |
| `strategy` | str | Anonymization strategy (default, presidio, fast, balanced, slm) |
| `file_name` | str | Input file name |
| `file_path` | str | Full path to input file |
| `file_extension` | str | File extension (lowercase, with dot) |
| `run_number` | int | Run iteration number |
| `timestamp` | str | ISO 8601 timestamp of run start |
| `status` | str | Run outcome: SUCCESS, FAILED, ERROR, TIMEOUT, SKIPPED |
| `error_message` | str | Error details (empty on success) |

### File Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `file_size_bytes` | int | bytes | Raw file size |
| `file_size_kb` | float | KB | File size in kilobytes |
| `file_size_mb` | float | MB | File size in megabytes |
| `character_count` | int | chars | Total characters (UTF-8, text files only) |
| `line_count` | int | lines | Total lines (text files only) |

### Time Metrics (from `/usr/bin/time -v`)

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `wall_clock_time_sec` | float | seconds | Total elapsed wall clock time |
| `user_time_sec` | float | seconds | CPU time spent in user mode |
| `system_time_sec` | float | seconds | CPU time spent in kernel mode |
| `cpu_percent` | float | % | Percentage of CPU this job received |

**Wall clock parsing:** Supports `ss.ss`, `m:ss.ss`, `h:mm:ss.ss`, and
`d-hh:mm:ss.ss` formats from GNU time.

### Memory Metrics (from `/usr/bin/time -v`)

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `max_resident_set_kb` | int | KB | Peak resident set size (RSS) |
| `average_resident_set_kb` | int | KB | Average RSS (often 0 on Linux) |
| `major_page_faults` | int | count | Page faults requiring disk I/O |
| `minor_page_faults` | int | count | Page faults served from memory |
| `voluntary_context_switches` | int | count | Process voluntarily yielded CPU |
| `involuntary_context_switches` | int | count | Process preempted by scheduler |

### I/O Metrics (from `/usr/bin/time -v`)

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `file_system_inputs` | int | blocks | Filesystem read operations |
| `file_system_outputs` | int | blocks | Filesystem write operations |

### Process Monitor Metrics (sampled at 500ms intervals)

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `avg_cpu_percent` | float | % | Average CPU usage (process + children) |
| `peak_cpu_percent` | float | % | Peak CPU usage observed |
| `avg_memory_mb` | float | MB | Average RSS (process + children) |
| `peak_memory_mb` | float | MB | Peak RSS observed |

### GPU Metrics (sampled via `nvidia-smi` at 500ms intervals)

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `gpu_available` | bool | - | Whether nvidia-smi was detected |
| `avg_gpu_utilization_percent` | float | % | Average GPU compute utilization |
| `peak_gpu_utilization_percent` | float | % | Peak GPU compute utilization |
| `avg_gpu_memory_used_mb` | float | MB | Average GPU memory (VRAM) used |
| `peak_gpu_memory_used_mb` | float | MB | Peak GPU memory (VRAM) used |
| `gpu_memory_total_mb` | float | MB | Total GPU memory available |
| `avg_gpu_temperature_c` | float | C | Average GPU temperature |
| `peak_gpu_temperature_c` | float | C | Peak GPU temperature |

GPU metrics are collected for the first GPU only (GPU 0). If `nvidia-smi`
is not available, all GPU fields default to 0 and `gpu_available` is `false`.

### Derived Metrics

| Metric | Type | Unit | Formula |
|--------|------|------|---------|
| `throughput_kb_per_sec` | float | KB/s | `file_size_kb / wall_clock_time_sec` |
| `throughput_mb_per_sec` | float | MB/s | `file_size_mb / wall_clock_time_sec` |
| `memory_per_kb_input` | float | KB/KB | `max_resident_set_kb / file_size_kb` |

---

## File Format Support Matrix

### Formats Supported by Each Version

| Extension | v1.0 | v2.0 | v3.0 | Category |
|-----------|:----:|:----:|:----:|----------|
| `.txt` | Y | Y | Y | Text |
| `.log` | - | - | Y | Text |
| `.csv` | Y | Y | Y | Structured |
| `.xlsx` | Y | Y | Y | Structured |
| `.xml` | Y | Y | Y | Structured |
| `.json` | - | Y | Y | Structured |
| `.jsonl` | - | - | Y | Structured |
| `.docx` | Y | Y | Y | Document |
| `.pdf` | - | Y | Y | Document |
| `.jpeg`/`.jpg` | - | Y | Y | Image |
| `.png` | - | Y | Y | Image |
| `.gif` | - | Y | Y | Image |
| `.bmp` | - | Y | Y | Image |
| `.tiff`/`.tif` | - | Y | Y | Image |
| `.webp` | - | - | Y | Image |
| `.jp2` | - | - | Y | Image |
| `.pnm` | - | - | Y | Image |

**Total formats:** v1.0 = 5, v2.0 = 13, v3.0 = 19

When a file's extension is not supported by a given version, the run is
marked as `SKIPPED` (not `FAILED`) and no processing time is recorded.

---

## Directory Structure

```
benchmark/
├── README.md                   # This documentation
├── ESTIMATES.md                # Auto-generated time estimates
├── benchmark.py                # Main benchmark suite (~1400 lines)
├── estimate.py                 # Time estimation tool (~510 lines)
├── analyze_benchmark.py        # Basic results analysis
├── analyze_benchmark_advanced.py  # Advanced statistical analysis
├── fix_benchmark_csv.py        # CSV repair utility
├── smoke_test_data/            # Minimal test data for validation
│   └── dados_teste/
│       ├── cve_dataset_mock_cais_stratified.csv
│       ├── cve_dataset_mock_cais_stratified.json
│       ├── teste-exemplo-artigo.txt
│       └── vulnnet_scans_openvas/
│           └── vulnnet_scans_openvas/
│               ├── openvas_alpine_3.7/
│               │   ├── openvas_alpine_3.7.csv
│               │   ├── openvas_alpine_3.7.pdf
│               │   ├── openvas_alpine_3.7.txt
│               │   └── openvas_alpine_3.7.xml
│               ├── exemplo.docx
│               └── exemplo.xlsx
├── results/                    # Benchmark output (auto-created)
│   ├── benchmark_results.csv   # All run metrics (append-only)
│   ├── benchmark_results.json  # Full results in JSON format
│   └── benchmark_state.json    # Resume state tracking
├── run_logs/                   # Per-run log files (auto-created)
│   ├── setup_v1.0.log
│   ├── setup_v2.0.log
│   ├── setup_v3.0.log
│   └── v{ver}_{strategy}_{file}_run{n}.log
└── output/                     # Anonymized output files (auto-created)
```

---

## Resume and Fault Tolerance

The benchmark suite is designed for multi-day campaigns where interruptions
are expected.

### How Resume Works

1. After each successful run, the run key (`version|strategy|file_name|run_number`)
   is added to `benchmark_state.json`.
2. On the next invocation, the orchestrator checks each planned run against
   the state file and skips already-completed runs.
3. Failed runs are tracked separately and are **not** skipped on retry,
   allowing transient failures to be retried.

### Interruption Handling

- **Ctrl+C (KeyboardInterrupt):** The orchestrator catches the signal, saves
  all collected results to JSON, and exits cleanly.
- **Process crash:** Since results are appended to CSV after each individual
  run and state is persisted immediately, at most one run's data is lost.
- **Power failure:** Same as crash -- resume picks up from the last completed run.

### State File Format

`benchmark/results/benchmark_state.json`:

```json
{
  "completed_runs": [
    "3.0|fast|openvas_alpine_3.7.txt|1",
    "3.0|presidio|teste-exemplo-artigo.txt|1"
  ],
  "failed_runs": [
    "1.0|default|openvas_alpine_3.7.pdf|1"
  ],
  "last_update": "2026-02-06T00:31:21.580106"
}
```

### Cleaning State

To start completely fresh:

```bash
python benchmark/benchmark.py --clean --benchmark --data-dir ./dados_teste
```

The `--clean` flag removes the entire `results/` directory before creating
the orchestrator, ensuring the CSV header and state are properly initialized.

---

## Output Files

### CSV Results (`benchmark_results.csv`)

Append-only CSV containing one row per benchmark run. All 40+ metrics are
included as columns. This is the primary data source for analysis.

- Headers are written on first run or after `--clean`.
- Rows are appended immediately after each run completes.
- Safe for incremental analysis during long campaigns.

### JSON Results (`benchmark_results.json`)

Complete JSON export of all metrics from the current session. Written at the
end of the benchmark phase (or on Ctrl+C). Useful for programmatic analysis.

### Run Logs (`run_logs/`)

Full stdout/stderr capture from each anonymization process, named:
`v{version}_{strategy}_{filename}_run{n}.log`

Also includes setup logs: `setup_v{version}.log`

---

## Methodology

### Measurement Modes

The benchmark supports three measurement modes, controlled by the
`measurement_mode` field in the output CSV:

| Mode | How | Overhead | Use Case |
|------|-----|----------|----------|
| `single_file` | One process per file | Included (~55-77s) | Per-file profiling, v1.0 compatibility |
| `directory_aggregate` | One process, all files | Once total | Fast batch measurement for v2.0/v3.0 |
| `directory_per_file` | Parsed from `[BENCHMARK_TIMING]` lines | Excluded | Pure processing throughput analysis |
| `overhead_calibration` | 5-byte file, isolating model load | IS the overhead | Measuring model loading cost |
| `regression` | Subsets of large files | Included | Predicting time for large files |

**Single-file mode** (default) processes each file in its own process
invocation. Every metric is available. Model loading overhead is included.

**Directory mode** (`--directory-mode`) passes a directory of files to
anon.py in a single invocation. Models load once, then all files are
processed sequentially. Per-file timing is extracted from `[BENCHMARK_TIMING]`
instrumentation lines emitted by the modified anon.py. Note: v1.0 does not
support directory mode and falls back to single-file automatically.

**Regression mode** (`--regression`) uses single-file mode on subsets of
large files to build a linear time-vs-size model for extrapolation.

### Metrics Collection Layers

1. **OS-level metrics** (`/usr/bin/time -v`): Wall clock time, user/system
   CPU time, peak RSS, page faults, context switches, I/O operations.
   These are the most reliable metrics as they come directly from the kernel.

2. **Process monitoring** (`psutil`): CPU and memory sampled at 500ms intervals
   via a background thread. Captures the process and all child processes
   recursively. Provides time-series behavior (average and peak) not available
   from `/usr/bin/time`.

3. **GPU monitoring** (`nvidia-smi`): GPU utilization, VRAM usage, and
   temperature sampled at 500ms intervals. Note this captures system-wide
   GPU usage, not per-process, so it is most accurate when no other GPU
   workloads are running.

4. **File-level metrics**: Size, character count, and line count collected
   before processing begins.

5. **Derived metrics**: Computed after collection -- throughput (KB/s, MB/s)
   and memory efficiency (KB RSS per KB input).

### Statistical Considerations

- **Multiple runs** (`--runs N`): Each configuration is run N times to enable
  statistical analysis (mean, standard deviation, confidence intervals).
  A minimum of 3 runs is recommended; 10 runs provides more robust estimates.

- **Warm cache assumption**: The setup phase warms model caches. First-run
  anomalies (if any) can be identified as outliers in multi-run data.

- **Secret key consistency**: The same `ANON_SECRET_KEY` is used across all
  runs to ensure deterministic anonymization output (given the same input).

### Reproducibility

To reproduce benchmark results:

1. Use the same machine and OS environment.
2. Ensure no competing workloads (CPU, GPU, I/O).
3. Use the same versions of AnonLFI (git commit hashes).
4. Use `--clean` to start from a fresh state.
5. Use the same `--secret-key` value.
6. Record the system specification (CPU model, RAM, GPU model, CUDA version).

---

## Known Limitations

1. **v3.0 fast strategy entity count:** The fast strategy may report 0
   detected entities. This is by design -- it uses xlm-roberta directly
   and only counts entities from `merged_entities`, which may be empty
   even when anonymization was performed.

2. **GPU metrics are system-wide:** `nvidia-smi` reports system-level GPU
   usage, not per-process. For accurate GPU measurements, ensure no other
   GPU workloads are running concurrently.

3. **Single-file processing overhead:** Each run includes full model loading
   overhead (transformer + spaCy models). This is intentional for measurement
   consistency but means throughput numbers underestimate batch processing
   performance.

4. **Large file memory pressure:** Files exceeding ~100 MB may cause memory
   pressure, especially with PDF and XLSX formats. Monitor system memory
   and consider reducing the number of concurrent processes.

5. **Wall clock time includes I/O:** The measured wall clock time includes
   file I/O (reading input, writing output), not just processing time.

6. **SLM strategy requires Ollama:** The `slm` strategy uses a local LLM
   via Ollama (default: llama3 at `localhost:11434`). Ollama must be running
   before starting the benchmark. Configure via `OLLAMA_BASE_URL` and
   `OLLAMA_MODEL` environment variables. SLM does not use Presidio engines,
   so `--use-datasets` and `--batch-size` flags are not applied.

---

## Troubleshooting

### `uv` not found

```
[ERROR] Setup failed: [Errno 2] No such file or directory: 'uv'
```

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The script searches `PATH`, `~/.local/bin/`, `~/.cargo/bin/`, and `/usr/local/bin/`.

### GPU torch installation fails

If CUDA is not available, use CPU mode:
```bash
python benchmark/benchmark.py --setup --cpu-only
```

### v1.0 fails on .pdf or .json files

This is expected. v1.0 only supports `.txt`, `.docx`, `.csv`, `.xlsx`, `.xml`.
These runs are marked as `SKIPPED`, not `FAILED`.

### Benchmark shows 0 progress

Ensure you have run `--setup` first. The benchmark phase requires virtual
environments to exist:
```bash
python benchmark/benchmark.py --setup
python benchmark/benchmark.py --benchmark --data-dir ./dados_teste
```

### CSV file has no headers

This occurs if `--clean` was not used and the CSV was corrupted. Fix:
```bash
python benchmark/benchmark.py --clean --benchmark --data-dir ./dados_teste
```

### v3.0 fails with "output file already exists"

The `--overwrite` flag is automatically added to v3.0 commands. If you see
this error, ensure you are using the latest version of `benchmark.py`.

### Process killed by OOM

Large files may exhaust system memory. Options:
- Use `--file-pattern` to exclude large files.
- Monitor with `htop` or `free -m` during runs.
- Add swap space: `sudo fallocate -l 8G /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`
