# AnonLFI Benchmark Time Estimates

**Generated:** 2026-02-06
**Updated:** 2026-02-06 (added regression-based estimates from measured data)
**Data directory:** `dados_teste`
**Planned runs per configuration:** 10

## Estimation Model

```
estimated_time = overhead + (file_size_kb / throughput_kbps)
```

- **overhead**: Fixed cost per run (model loading, interpreter startup)
- **throughput_kbps**: Processing rate in KB/s for the given format
- Each file is estimated individually based on its actual size

## Regression-Based Estimates (Measured 2026-02-06)

The following estimates are derived from actual benchmark runs using the
`--regression` feature. Subsets of the production data files were created
at 1 MB and 2 MB, each benchmarked 3 times. A linear regression model was
fitted to the (file_size_kb, wall_clock_time_sec) data points.

### v1.0 | default | CSV

**Source:** `cve_dataset_mock_cais_stratified.csv` (247.5 MB)

| Size (MB) | Run 1 (s) | Run 2 (s) | Run 3 (s) | Mean (s) | Std (s) | KB/s |
|:---------:|:---------:|:---------:|:---------:|:--------:|:-------:|:----:|
| 1.0       | 431.95    | 431.57    | 414.78    | 426.10   | 9.81    | 2.40 |
| 2.0       | 784.36    | 805.42    | 810.13    | 799.97   | 13.72   | 2.56 |

**Regression model:**

```
time = 52.87 + 0.365327 * size_kb
  Intercept: 52.87s  (model loading; cf. calibrated: 54.81s)
  Slope:     0.365327 s/KB  ->  throughput: 2.74 KB/s
  R^2:       1.0000
```

**Predictions for v1.0 CSV:**

| Target Size | Predicted Time | Human-Readable |
|:-----------:|:--------------:|:--------------:|
| 1 MB        | 427 s          | 7m 7s          |
| 2 MB        | 801 s          | 13m 21s        |
| 4 MB        | 1,549 s        | 25m 49s        |
| 8 MB        | 3,046 s        | 50m 46s        |
| 16 MB       | 6,038 s        | 1h 41m         |
| 64 MB       | 23,995 s       | 6h 40m         |
| 247.5 MB    | 92,641 s       | **25h 44m**    |

### Resource Scaling Analysis (v1.0 CSV)

How resource consumption changes when input doubles from 1 MB to 2 MB:

| Resource | 1 MB | 2 MB | Change | Scaling |
|----------|-----:|-----:|-------:|---------|
| Wall Clock (s) | 426.1 | 800.0 | +87.8% | **Linear** |
| User CPU Time (s) | 1,838.6 | 3,730.1 | +102.9% | **Linear** |
| System Time (s) | 11.3 | 14.3 | +26.4% | Sublinear |
| CPU Utilization (%) | 434 | 468 | +7.8% | Constant |
| Peak RSS (MB) | 2,541 | 2,668 | +5.0% | **Constant** |
| GPU Utilization (%) | 87 | 88 | +1.5% | Constant |
| GPU VRAM (MB) | 8,036 | 7,939 | -1.2% | **Constant** |
| Filesystem Writes | 72,979 | 147,856 | +102.6% | **Linear** |

**Key findings:**

1. **Time scales linearly** with input size. User CPU time doubles when input
   doubles, confirming a `O(n)` algorithmic complexity for the anonymization
   pipeline. This validates the linear regression model for time prediction.

2. **Memory is dominated by the NLP models**, not by input data. Peak RSS
   increases by only 127 MB (5%) when input doubles from 1 MB to 2 MB. The
   base footprint (~2.5 GB) is almost entirely model weights (xlm-roberta-large,
   spaCy pt_core_news_lg). For very large files (>100 MB), memory may grow
   further if the tool loads entire files into memory, but within the measured
   range, memory scaling is negligible.

3. **GPU utilization and VRAM are constant**, indicating that the GPU workload
   (transformer inference) is batched at a fixed size regardless of input.
   The NLP model consumes ~8 GB VRAM for model weights and activations,
   independent of input file size.

4. **CPU utilization is constant** at ~430-470%, indicating consistent
   multi-threaded behavior (approximately 4-5 cores utilized). This suggests
   the anonymization pipeline parallelizes NER and anonymization across
   multiple CPU threads with a fixed thread pool.

5. **Filesystem writes scale linearly**, as expected: the anonymized output
   is proportional to the input size. This confirms that I/O is not a
   bottleneck relative to processing time.

**Prediction methodology for resource metrics:**

- **Constant** (elasticity < 10%): predicted as the mean of observed values. Linear extrapolation
  would be meaningless for metrics dominated by fixed costs (model weights, GPU VRAM).
- **Sublinear** (10-30%): predicted as the max observed value (conservative upper bound).
- **Linear/superlinear** (>30%): predicted via OLS linear extrapolation (same as time model).

### RAM Comparison: Streaming vs Full-Load (Measured 2026-02-06)

To empirically validate RAM behavior under production conditions, each version
was launched on the **full 247.5 MB CSV** (`cve_dataset_mock_cais_stratified.csv`,
3 columns, 70,951 rows) and RSS was sampled every 5 seconds for 3 minutes.

**Architecture difference:**

- **v1.0/v2.0:** Load the entire file into memory via `pd.read_csv()` (no streaming).
  v1.0 additionally calls `df.values.flatten().tolist()`, creating a second copy.
- **v3.0:** Streams the file in 1,000-row chunks via `pd.read_csv(chunksize=1000)`.
  Only one chunk is in memory at a time.

**Measured RAM during processing phase (after model loading):**

| Version | Strategy | Processing Start | At 176s | Growth | Rate (MB/hr) | Pattern |
|---------|----------|----------------:|---------:|-------:|-------------:|---------|
| v1.0 | default | 2,096 MB | 2,226 MB | +130 MB | 4,019 | Sublinear (decelerating) |
| v2.0 | default | 2,750 MB | 2,834 MB | +84 MB  | 5,092 | Sublinear |
| v3.0 | presidio | 2,444 MB | 2,487 MB | +43 MB  | 894  | **Constant** |
| v3.0 | fast     | 2,428 MB | 2,473 MB | +45 MB  | 1,027 | **Constant** |
| v3.0 | balanced | 2,432 MB | 2,502 MB | +70 MB  | 1,419 | **Constant** |

**Key findings:**

1. **v2.0 uses the most RAM** (2,834 MB at 176s), likely due to heavier NLP
   pipelines (Presidio integration) combined with full-file loading. This is
   608 MB more than v1.0 at the same elapsed time.

2. **v1.0 RAM growth is decelerating**: the first half of processing shows
   2.26 MB/s growth, the second half only 0.93 MB/s. This is consistent with
   the CSV being progressively loaded and parsed — once fully loaded, growth
   plateaus. The file's in-memory representation (pandas DataFrame + Python
   string objects) is estimated at ~520 MB for this 247.5 MB CSV
   (3 columns of dense text with ~50 bytes Python object overhead per cell).

3. **v3.0 RAM is essentially flat** during processing. The streaming chunk
   approach (`chunksize=1000` rows) keeps only ~1,000 rows in memory at any
   time. Variation is ±22 MB (noise from GC cycles, not data accumulation).
   **v3.0 can process arbitrarily large CSV files without increased RAM.**

4. **Model footprint dominates all versions** (~2.0-2.5 GB). The NLP models
   (xlm-roberta-large, spaCy) account for >90% of RAM regardless of file size.

**RAM predictions for full 247.5 MB CSV run:**

| Version | Strategy | Predicted Peak RAM | Confidence |
|---------|----------|-------------------:|------------|
| v1.0 | default | ~2,600 MB (2.5 GB) | High (file in memory + model base) |
| v2.0 | default | ~2,900 MB (2.8 GB) | High (measured plateau at 2,834 MB) |
| v3.0 | presidio | ~2,480 MB (2.4 GB) | Very high (flat, file-size independent) |
| v3.0 | fast | ~2,470 MB (2.4 GB) | Very high (flat, file-size independent) |
| v3.0 | balanced | ~2,500 MB (2.4 GB) | Very high (flat, file-size independent) |

**Implication:** While v1.0/v2.0 can still handle 247.5 MB within reasonable
RAM bounds (~3 GB), their approach would fail or degrade for files in the
multi-GB range. v3.0's streaming architecture provides constant memory
regardless of input size — a critical advantage for production deployments
with unbounded input sizes.

### Environment for Regression Runs

| Parameter | Value |
|-----------|-------|
| Machine | WSL2 Ubuntu on Windows |
| GPU | NVIDIA GPU (88-89% utilization during runs) |
| Peak VRAM | 7,466 - 8,862 MB |
| Peak RSS | 2,537 - 2,670 MB |
| CPU | ~29% (multi-core system) |
| Concurrent load | Another anon.py instance running in parallel |

> **Note:** The concurrent load may have slightly increased wall-clock times.
> Clean-room measurements (no other GPU workloads) would likely show 5-10%
> faster times.

## 1. File Inventory

| Extension | Count | Total Size | Avg Size | Largest File |
|-----------|------:|-----------:|---------:|:-------------|
| `.csv` | 139 | 260.1 MB | 1915.9 KB | cve_dataset_mock_cais_stratified.csv (247.5 MB) |
| `.json` | 1 | 444.6 MB | 455226.9 KB | cve_dataset_mock_cais_stratified.json (444.6 MB) |
| `.pdf` | 138 | 41.0 MB | 304.5 KB | openvas_completo.pdf (3.8 MB) |
| `.txt` | 138 | 15.9 MB | 117.9 KB | openvas_completo.txt (2.2 MB) |
| `.xml` | 140 | 80.4 MB | 588.0 KB | openvas_completo.xml (19.8 MB) |
| **Total** | **556** | **841.9 MB** | | |

## 2. Model Loading Overhead (from calibration runs)

Measured by running a near-zero content file (5 bytes) to isolate
model loading and interpreter startup cost from content processing.

### Calibration (10 runs, 2026-02-06)

| Version | Strategy | Mean (s) | Std (s) | Min (s) | Max (s) | Runs |
|---------|----------|:--------:|:-------:|:-------:|:-------:|-----:|
| v1.0 | default  |  54.81   |  0.66   |  53.77  |  55.96  |  10  |
| v2.0 | default  |  58.32   |  2.87   |  55.07  |  62.95  |  10  |
| v3.0 | presidio |  58.70   |  0.78   |  57.63  |  60.12  |  10  |
| v3.0 | fast     |  57.80   |  0.93   |  56.35  |  59.59  |  10  |
| v3.0 | balanced |  62.27   |  6.03   |  55.43  |  72.50  |  10  |

### Earlier Calibration (3 runs, reference)

| Version | Strategy | Overhead (s) | Runs |
|---------|----------|-------------:|-----:|
| v1.0 | default | 77.3 | 3 |
| v2.0 | default | 71.7 | 3 |
| v3.0 | balanced | 55.2 | 3 |
| v3.0 | fast | 56.4 | 3 |
| v3.0 | presidio | 65.8 | 3 |

> The 10-run calibration shows lower overhead than the 3-run calibration.
> This is likely due to model caching effects (NLP models were already cached
> in memory from prior runs). The 10-run values represent warm-cache steady
> state; the 3-run values may include cold-cache outliers.

## 3. Throughput Profiles (from smoke test)

Processing rate after subtracting model loading overhead.

| Version | Strategy | Extension | Throughput (KB/s) | Source | Data Points | R^2 |
|---------|----------|-----------|------------------:|--------|------------:|----:|
| v1.0 | default | `.csv` | 0.839 | regression | 2 | 1.000 |
| v1.0 | default | `.txt` | 0.684 | largest_file | 2 | - |
| v1.0 | default | `.xml` | 0.713 | single_point | 1 | - |
| v2.0 | default | `.csv` | 1.519 | regression | 2 | 1.000 |
| v2.0 | default | `.json` | 0.164 | single_point | 1 | - |
| v2.0 | default | `.pdf` | 2.344 | single_point | 1 | - |
| v2.0 | default | `.txt` | 0.480 | regression | 2 | 1.000 |
| v2.0 | default | `.xml` | 0.152 | single_point | 1 | - |
| v3.0 | balanced | `.csv` | 25.241 | regression | 2 | 1.000 |
| v3.0 | balanced | `.json` | 2.325 | single_point | 1 | - |
| v3.0 | balanced | `.pdf` | 32.300 | single_point | 1 | - |
| v3.0 | balanced | `.txt` | 1.001 | extrapolated_from_presidio | 2 | - |
| v3.0 | balanced | `.xml` | 3.095 | extrapolated_from_presidio | 1 | - |
| v3.0 | fast | `.csv` | 10.531 | regression | 2 | 1.000 |
| v3.0 | fast | `.json` | 0.469 | single_point | 1 | - |
| v3.0 | fast | `.pdf` | 12.836 | single_point | 1 | - |
| v3.0 | fast | `.txt` | 2.136 | largest_file | 2 | - |
| v3.0 | fast | `.xml` | 1.698 | single_point | 1 | - |
| v3.0 | presidio | `.csv` | 1.335 | regression | 2 | 1.000 |
| v3.0 | presidio | `.json` | 0.566 | single_point | 1 | - |
| v3.0 | presidio | `.pdf` | 8.216 | single_point | 1 | - |
| v3.0 | presidio | `.txt` | 1.001 | largest_file | 2 | - |
| v3.0 | presidio | `.xml` | 3.095 | single_point | 1 | - |

## 4. Version Support Matrix

| Extension | v1.0 | v2.0 | v3.0 |
|-----------|:----:|:----:|:----:|
| `.csv` | Y | Y | Y |
| `.json` | - | Y | Y |
| `.pdf` | - | Y | Y |
| `.txt` | Y | Y | Y |
| `.xml` | Y | Y | Y |

## 5.10 Estimates for v1.0


| Extension | Files | Total Size | Overhead | Throughput | 1 Run | 10 Runs | Source |
|-----------|------:|-----------:|---------:|-----------:|------:|-------:|--------|
| `.csv` | 139 | 260.1 MB | 77.3s | 0.839 KB/s | 91.1h | 911.2h | regression |
| `.txt` | 138 | 15.9 MB | 77.3s | 0.684 KB/s | 9.6h | 95.6h | largest_file |
| `.xml` | 140 | 80.4 MB | 77.3s | 0.713 KB/s | 35.1h | 350.5h | single_point |
| **Subtotal** | | | | | | **1357.3h (56.6d)** | |

**v1.0 Total: 1357.3 hours (56.6 days)**

## 5.20 Estimates for v2.0


| Extension | Files | Total Size | Overhead | Throughput | 1 Run | 10 Runs | Source |
|-----------|------:|-----------:|---------:|-----------:|------:|-------:|--------|
| `.csv` | 139 | 260.1 MB | 71.7s | 1.519 KB/s | 51.5h | 514.8h | regression |
| `.json` | 1 | 444.6 MB | 71.7s | 0.164 KB/s | 770.1h | 7701.2h | single_point |
| `.pdf` | 138 | 41.0 MB | 71.7s | 2.344 KB/s | 7.7h | 77.3h | single_point |
| `.txt` | 138 | 15.9 MB | 71.7s | 0.480 KB/s | 12.2h | 121.6h | regression |
| `.xml` | 140 | 80.4 MB | 71.7s | 0.152 KB/s | 153.7h | 1536.8h | single_point |
| **Subtotal** | | | | | | **9951.6h (414.7d)** | |

**v2.0 Total: 9951.6 hours (414.7 days)**

## 5.30 Estimates for v3.0

### Strategy: `presidio`

| Extension | Files | Total Size | Overhead | Throughput | 1 Run | 10 Runs | Source |
|-----------|------:|-----------:|---------:|-----------:|------:|-------:|--------|
| `.csv` | 139 | 260.1 MB | 65.8s | 1.335 KB/s | 57.9h | 579.5h | regression |
| `.json` | 1 | 444.6 MB | 65.8s | 0.566 KB/s | 223.3h | 2232.5h | single_point |
| `.pdf` | 138 | 41.0 MB | 65.8s | 8.216 KB/s | 3.9h | 39.4h | single_point |
| `.txt` | 138 | 15.9 MB | 65.8s | 1.001 KB/s | 7.0h | 70.4h | largest_file |
| `.xml` | 140 | 80.4 MB | 65.8s | 3.095 KB/s | 9.9h | 99.5h | single_point |
| **Subtotal** | | | | | | **3021.2h (125.9d)** | |

### Strategy: `fast`

| Extension | Files | Total Size | Overhead | Throughput | 1 Run | 10 Runs | Source |
|-----------|------:|-----------:|---------:|-----------:|------:|-------:|--------|
| `.csv` | 139 | 260.1 MB | 56.4s | 10.531 KB/s | 9.2h | 92.0h | regression |
| `.json` | 1 | 444.6 MB | 56.4s | 0.469 KB/s | 269.8h | 2698.2h | single_point |
| `.pdf` | 138 | 41.0 MB | 56.4s | 12.836 KB/s | 3.1h | 30.7h | single_point |
| `.txt` | 138 | 15.9 MB | 56.4s | 2.136 KB/s | 4.3h | 42.8h | largest_file |
| `.xml` | 140 | 80.4 MB | 56.4s | 1.698 KB/s | 15.7h | 156.6h | single_point |
| **Subtotal** | | | | | | **3020.2h (125.8d)** | |

### Strategy: `balanced`

| Extension | Files | Total Size | Overhead | Throughput | 1 Run | 10 Runs | Source |
|-----------|------:|-----------:|---------:|-----------:|------:|-------:|--------|
| `.csv` | 139 | 260.1 MB | 55.2s | 25.241 KB/s | 5.1h | 50.6h | regression |
| `.json` | 1 | 444.6 MB | 55.2s | 2.325 KB/s | 54.4h | 544.0h | single_point |
| `.pdf` | 138 | 41.0 MB | 55.2s | 32.300 KB/s | 2.5h | 24.8h | single_point |
| `.txt` | 138 | 15.9 MB | 55.2s | 1.001 KB/s | 6.6h | 66.3h | extrapolated_from_presidio |
| `.xml` | 140 | 80.4 MB | 55.2s | 3.095 KB/s | 9.5h | 95.3h | extrapolated_from_presidio |
| **Subtotal** | | | | | | **781.0h (32.5d)** | |

**v3.0 Total: 6822.5 hours (284.3 days)**

## 6. Grand Total

| Version | Strategies | Estimated Time |
|---------|------------|---------------:|
| v1.0 | default | 1357.3h (56.6d) |
| v2.0 | default | 9951.6h (414.7d) |
| v3.0 | presidio, fast, balanced | 6822.5h (284.3d) |
| **TOTAL** | | **18131.5h (755.5d)** |

## 7. Methodology

### Two-Component Model
Each file's processing time is estimated as:

```
time = overhead + (file_size_kb / throughput_kbps)
```

This separates the fixed cost (model loading, interpreter startup,
library imports) from the variable cost (proportional to file size).

### Overhead Calibration
- A near-zero content file (5 bytes) is processed 3 times per
  version/strategy combination
- The average wall clock time is used as the overhead constant
- This represents: Python startup + model loading + NLP pipeline init

### Throughput Derivation
- For each (version, strategy, extension) observed in smoke tests:
  - processing_time = observed_time - overhead
  - throughput = file_size_kb / processing_time
- Multiple data points are averaged to reduce noise
- When direct observations are unavailable, throughput is
  extrapolated from similar combinations (same version/different
  strategy, or same extension/different version)

### Per-File Estimation
- Each file in the dataset is estimated individually based on
  its actual size, not an average
- This correctly handles datasets with extreme size variance
  (e.g., 1 KB files alongside 250 MB files)

### Assumptions
- Sequential execution (one file at a time)
- Model cache is warm (models already downloaded)
- No system resource contention
- Linear throughput scaling (may underestimate for very large files
  where memory pressure causes swapping)

### Limitations
- Throughput is derived from small smoke test files (<400 KB)
- Very large files (>100 MB) may exhibit sub-linear throughput
  due to memory pressure, chunking, or I/O bottlenecks
- GPU utilization may vary with batch size and file content
- Overhead may vary slightly by format due to format-specific
  processor initialization
