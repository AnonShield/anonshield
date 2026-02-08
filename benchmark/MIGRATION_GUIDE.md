## 🔄 Migration Guide: Old → New Visualization System

### Overview of Changes

The benchmark visualization system has been completely refactored to fix critical scientific issues and add missing analyses required for high-impact publications.

---

## 🔴 Critical Issues Fixed

### Issue #1: Invalid "Time by Format" Comparisons

**❌ OLD CODE (analyze_benchmark_advanced.py, visualization_individual.py)**

```python
# PROBLEM: Comparing raw execution time across file formats
# Different formats have vastly different file sizes!
# Example: PDF (50 MB) vs TXT (5 KB) - of course PDF takes longer!

# visualization_individual.py lines 279-308
def plot_performance_matrix(self, data, output_path):
    pivot = data.pivot_table(
        values='wall_clock_time_sec',  # ❌ RAW TIME - NOT NORMALIZED
        index='version_strategy',
        columns='file_extension',
        aggfunc='mean'
    )
    sns.heatmap(pivot, ...)  # ❌ MISLEADING COMPARISON
```

**✅ NEW CODE (visualization/charts.py)**

```python
# SOLUTION: Normalize by file size
def create_normalized_performance_comparison(self, data, output_path):
    # Compute time per MB - fair comparison!
    data['time_per_mb'] = data['wall_clock_time_sec'] / data['file_size_mb']

    pivot = data.pivot_table(
        values='time_per_mb',  # ✅ NORMALIZED METRIC
        index='version_strategy',
        columns='file_extension',
        aggfunc='mean'
    )
```

**Impact:** This was producing scientifically invalid conclusions. A strategy could appear "slower" for PDFs simply because PDF files were larger, not because the algorithm was less efficient.

---

### Issue #2: Missing Statistical Rigor

**❌ OLD: Only p-values, no effect sizes**

```python
# OLD: Just significance stars
if p_value < 0.05:
    stars = '*'
# But HOW MUCH difference? Small but significant? Large but not significant?
```

**✅ NEW: Effect sizes + confidence intervals**

```python
# Calculate Cohen's d with 95% CI
effect = EffectSizeCalculator.cohens_d(group1, group2, ci_level=0.95)
print(f"Cohen's d: {effect.value:.3f} [{effect.ci_lower:.3f}, {effect.ci_upper:.3f}]")
print(f"Interpretation: {effect.interpretation}")  # "small", "medium", "large"
```

**Impact:** Reviewers will reject papers that only report p-values without effect sizes. See: [ASA Statement on P-Values (2016)](https://www.tandfonline.com/doi/full/10.1080/00031305.2016.1154108)

---

### Issue #3: No Multiple Comparison Correction

**❌ OLD: Running 10+ t-tests without correction**

```python
# If you run 20 comparisons at α=0.05, you expect 1 false positive!
# Old code did NOT correct for this
for strategy1, strategy2 in combinations(strategies, 2):
    _, p_value = stats.mannwhitneyu(data1, data2)
    if p_value < 0.05:  # ❌ UNCORRECTED!
        print(f"{strategy1} vs {strategy2}: significant")
```

**✅ NEW: FDR correction (Benjamini-Hochberg)**

```python
# Collect all p-values
p_values = [test_result['p_value'] for test_result in all_tests]

# Apply correction
correction = StatisticalAnalyzer.multiple_comparison_correction(
    p_values, method='fdr_bh', alpha=0.05
)

# Use corrected p-values
for i, (original_p, corrected_p) in enumerate(zip(p_values, correction['p_values_corrected'])):
    if correction['reject_null'][i]:
        print(f"Significant after correction: p_corrected={corrected_p:.4f}")
```

**Impact:** Without correction, you're likely reporting false discoveries. Journals will reject this.

---

### Issue #4: Missing Overhead Analysis

**❌ OLD: No decomposition of execution time**

```python
# What contributes to execution time?
# - Model loading overhead (fixed)
# - Processing time (scales with file size)
# Old code didn't separate these!
```

**✅ NEW: Overhead model with regression**

```python
# Model: time = overhead + (file_size / throughput)
model = RegressionAnalyzer.overhead_model(file_sizes_kb, times_sec)

print(f"Fixed overhead: {model.overhead_sec:.1f} seconds")
print(f"Processing throughput: {model.throughput_kb_per_sec:.2f} KB/s")
print(f"R² = {model.r_squared:.3f}")

# This tells you:
# - If improvement is from faster model loading OR faster processing
# - How performance scales with file size
# - Whether bottleneck is CPU or I/O
```

**Impact:** Essential for understanding WHERE optimizations should focus.

---

## 📊 New Visualizations Added

| Visualization | Purpose | Key Insight |
|--------------|---------|-------------|
| **Normalized Performance** | Time per MB across formats | Fair comparison accounting for file size |
| **Effect Size Forest Plot** | Cohen's d with CI | Magnitude of differences, not just significance |
| **Overhead Decomposition** | Fixed vs. scalable costs | Where optimizations should target |
| **Q-Q Normality Plots** | Validate statistical assumptions | Know if parametric tests are valid |
| **Pairwise Significance Heatmap** | All comparisons with FDR correction | Control false discovery rate |
| **Advanced Distribution** | Violin + KDE + ECDF | Full distributional understanding |
| **Resource Efficiency** | Memory/CPU/I/O per unit work | Identify bottlenecks |

---

## 🚀 Migration Steps

### Step 1: Install Dependencies

```bash
# The new system requires statsmodels
pip install statsmodels

# Verify all dependencies
pip install numpy pandas matplotlib seaborn scipy statsmodels
```

### Step 2: Use New Analysis Script

**OLD:**
```bash
python benchmark/analyze_benchmark_advanced.py results.csv
```

**NEW:**
```bash
python benchmark/analyze_benchmark_scientific.py results.csv
```

### Step 3: Review Output Differences

**OLD OUTPUT:**
```
benchmark/results/analysis/
├── strategy_comparison.png      # ❌ Raw time, not normalized
├── format_analysis.png          # ❌ Raw time by format
├── performance_matrix.png       # ❌ CRITICAL ISSUE: not normalized
└── ...
```

**NEW OUTPUT:**
```
benchmark/results/scientific/
├── 01_normalized_performance.png/pdf    # ✅ Time per MB (fixed!)
├── 02_effect_size_comparison.png/pdf   # ✅ Cohen's d forest plot
├── 03_overhead_decomposition.png/pdf   # ✅ Regression analysis
├── 04_qq_normality_plots.png/pdf       # ✅ Assumption validation
├── 05_pairwise_significance.png/pdf    # ✅ FDR-corrected heatmap
├── 06_distribution_analysis.png/pdf    # ✅ Violin + KDE + ECDF
├── 07_resource_efficiency.png/pdf      # ✅ Normalized efficiency
└── statistical_report.txt              # ✅ Summary stats
```

---

## 📖 Usage Examples

### Example 1: Quick Analysis

```python
from benchmark.analyze_benchmark_scientific import ScientificBenchmarkAnalyzer

# Load and analyze
analyzer = ScientificBenchmarkAnalyzer('results.csv', mode='paper')
analyzer.run_complete_analysis(baseline_strategy='3.0_presidio')

# Output: 7 publication-ready figures + statistical report
```

### Example 2: Custom Visualization

```python
from visualization import VisualizationConfig, ChartFactory
import pandas as pd

# Load data
data = pd.read_csv('results.csv')

# Configure for presentation (larger fonts)
config = VisualizationConfig(mode='presentation')
config.apply()

# Create specific chart
factory = ChartFactory(config)
factory.performance.create_normalized_performance_comparison(
    data, 'output/normalized_perf'
)
```

### Example 3: Statistical Analysis Only

```python
from visualization.statistics import StatisticalAnalyzer, EffectSizeCalculator
import pandas as pd

data = pd.read_csv('results.csv')

# Test normality
analyzer = StatisticalAnalyzer()
for strategy in data['version_strategy'].unique():
    subset = data[data['version_strategy'] == strategy]['wall_clock_time_sec'].values
    result = analyzer.test_normality(subset)
    print(f"{strategy}: {'Normal' if result['is_normal'] else 'Non-normal'}")

# Calculate effect sizes
effect_calc = EffectSizeCalculator()
group1 = data[data['version_strategy'] == '3.0_presidio']['wall_clock_time_sec'].values
group2 = data[data['version_strategy'] == '3.0_filtered']['wall_clock_time_sec'].values

effect = effect_calc.cohens_d(group1, group2)
print(f"Effect size: {effect.value:.3f} ({effect.interpretation})")
```

---

## 🎨 Visual Design Changes

### Color Scheme

**OLD:** Random seaborn palettes (not colorblind-safe)

**NEW:** Wong (2011) palette - verified colorblind-safe
- Blue (#0072B2), Orange (#E69F00), Green (#009E73), etc.
- Scientifically validated for all types of colorblindness

### Figure Sizes

**OLD:** Arbitrary sizes (16x6, 12x10, etc.)

**NEW:** IEEE publication standards
- Single column: 3.5" × 2.625"
- Double column: 7.0" × 5.25"
- Matches journal requirements (Nature, Science, IEEE, PLOS)

### DPI

**OLD:** 150 DPI (screen only)

**NEW:**
- Screen preview: 100 DPI
- Paper output: 300 DPI
- High-quality: 600 DPI

### File Formats

**OLD:** PNG only

**NEW:** Both PNG (raster) and PDF (vector)
- PNG for presentations, websites
- PDF for publications (scalable, no quality loss)

---

## ⚠️ Breaking Changes

### 1. Different Output Structure

Old scripts will NOT work with new output directory structure.

**Migration:**
```python
# OLD
output_path = "benchmark/results/analysis/strategy_comparison.png"

# NEW
output_path = "benchmark/results/scientific/01_normalized_performance.png"
```

### 2. Different Data Requirements

New system expects these columns (same as before, but now strictly required):

**Required:**
- `version`, `strategy`, `version_strategy`
- `file_extension`, `file_name`
- `file_size_mb`, `file_size_kb`
- `wall_clock_time_sec`
- `status` (for filtering)

**Recommended (for full analysis):**
- `user_time_sec`, `system_time_sec`
- `peak_memory_mb`, `max_resident_set_kb`
- `cpu_percent`, `io_wait_percent`
- `throughput_mb_per_sec`

### 3. API Changes

If you were importing from old modules:

```python
# ❌ OLD (deprecated)
from analyze_benchmark_advanced import BenchmarkAnalyzer

# ✅ NEW
from benchmark.analyze_benchmark_scientific import ScientificBenchmarkAnalyzer
# OR for components
from visualization import VisualizationConfig, ChartFactory
```

---

## 🧪 Testing

Run the test suite to verify installation:

```bash
python benchmark/test_scientific_viz.py
```

This will:
1. Generate synthetic benchmark data
2. Create all 7 visualizations
3. Save to `benchmark/results/test_scientific/`
4. Report any errors

---

## 📚 Further Reading

### Scientific Best Practices
1. **American Statistical Association Statement on P-Values**
   - https://www.tandfonline.com/doi/full/10.1080/00031305.2016.1154108

2. **Reporting Effect Sizes in Psychology**
   - Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences*

3. **Multiple Comparison Corrections**
   - Benjamini & Hochberg (1995). *Controlling the False Discovery Rate*

4. **Colorblind-Safe Visualizations**
   - Wong, B. (2011). Points of view: Color blindness. *Nature Methods*

### Code Quality
- SOLID Principles: https://en.wikipedia.org/wiki/SOLID
- Design Patterns (Factory, Template Method, Strategy)

---

## 💬 Support

For issues or questions:
1. Check `visualization/README.md` for detailed API documentation
2. Run `python benchmark/test_scientific_viz.py` to diagnose problems
3. Review example output in `benchmark/results/test_scientific/`

---

## ✅ Checklist for Paper Submission

Before submitting to a journal/conference, verify:

- [ ] All figures use normalized metrics (not raw time by format)
- [ ] Effect sizes reported with confidence intervals
- [ ] Multiple comparison corrections applied (FDR/Bonferroni)
- [ ] Normality assumptions tested (Q-Q plots included)
- [ ] Regression models include R², p-values, and diagnostics
- [ ] Figures are colorblind-safe (Wong palette)
- [ ] Figure sizes match journal requirements (check author guidelines)
- [ ] Both PNG (300 DPI) and PDF versions generated
- [ ] Statistical report includes all test details

---

**Version:** 3.0.0
**Last Updated:** 2026-02-08
**Authors:** AnonShield Team
