# Scientific Visualization Module

Publication-quality benchmark visualizations following SOLID principles and scientific standards.

## Overview

This module provides a complete refactoring of the benchmark analysis system with:

- ✅ **Fixed critical issues**: Removed misleading "time by format" comparisons without size normalization
- ✅ **Publication-ready**: IEEE-standard figure sizes, 300 DPI, colorblind-safe palettes
- ✅ **Scientifically rigorous**: Effect sizes, multiple comparison corrections, regression diagnostics
- ✅ **Modular architecture**: SOLID principles, factory pattern, separation of concerns

## Architecture

```
visualization/
├── __init__.py           # Module exports
├── config.py             # Configuration (colors, sizes, typography)
├── statistics.py         # Statistical analysis (effect sizes, tests, regression)
├── charts.py             # Chart factories (performance, statistical, regression, etc.)
└── README.md            # This file
```

### Key Components

#### 1. `config.py` - Configuration System

```python
from visualization import VisualizationConfig

# Initialize for publication mode
config = VisualizationConfig(mode='paper')
config.apply()

# Get figure sizes
fig_size = config.get_figure_size('double_wide')  # (7.0, 4.0) inches

# Get colorblind-safe colors
colors = config.get_colors(n=5)

# Save figures
config.save_figure(fig, 'output_path')  # Saves both PNG and PDF
```

**Features:**
- Colorblind-safe palettes (Wong 2011, Nature Methods)
- Publication-standard sizes (IEEE, Nature, PLOS)
- High-DPI output (300-600 DPI)
- Three modes: `paper`, `presentation`, `screen`

#### 2. `statistics.py` - Statistical Analysis

```python
from visualization import StatisticalAnalyzer, EffectSizeCalculator, RegressionAnalyzer

# Effect sizes
effect = EffectSizeCalculator.cohens_d(group1, group2, ci_level=0.95)
print(f"Cohen's d: {effect.value:.3f} ({effect.interpretation})")
print(f"95% CI: [{effect.ci_lower:.3f}, {effect.ci_upper:.3f}]")

# Statistical tests
analyzer = StatisticalAnalyzer()
normality = analyzer.test_normality(data)  # Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling

# Multiple comparison correction
correction = analyzer.multiple_comparison_correction(p_values, method='fdr_bh')

# Regression analysis
reg = RegressionAnalyzer.linear_regression(x, y, confidence=0.95)
print(f"R² = {reg.r_squared:.3f}, p = {reg.p_value:.4f}")

# Overhead model: time = overhead + size/throughput
model = RegressionAnalyzer.overhead_model(file_sizes_kb, times_sec)
print(f"Overhead: {model.overhead_sec:.1f}s, Throughput: {model.throughput_kb_per_sec:.2f} KB/s")
```

**Features:**
- Effect sizes: Cohen's d, Hedges' g (with CI)
- Multiple tests: Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling, Mann-Whitney
- Multiple comparison corrections: Bonferroni, Holm, FDR (Benjamini-Hochberg)
- Regression: Linear, robust (Huber), with diagnostics
- Overhead decomposition: `time = overhead + size/throughput`

#### 3. `charts.py` - Chart Factory

```python
from visualization import ChartFactory, VisualizationConfig

config = VisualizationConfig(mode='paper')
factory = ChartFactory(config)

# Normalized performance (CRITICAL FIX)
factory.performance.create_normalized_performance_comparison(data, 'output/01_normalized')

# Effect size comparison
factory.performance.create_effect_size_comparison(data, baseline_strategy, 'output/02_effect_size')

# Overhead decomposition
factory.regression.create_overhead_decomposition(data, 'version_strategy', 'output/03_overhead')

# Q-Q normality plots
factory.regression.create_qq_normality_plots(data, 'version_strategy', 'wall_clock_time_sec', 'output/04_qq')

# Pairwise significance
factory.statistical.create_pairwise_significance_heatmap(
    data, 'version_strategy', 'wall_clock_time_sec', correction_method='fdr_bh', 'output/05_pairwise'
)

# Distribution analysis
factory.distribution.create_advanced_distribution(data, 'version_strategy', 'wall_clock_time_sec', 'output/06_dist')

# Resource efficiency
factory.resource.create_resource_efficiency_analysis(data, 'version_strategy', 'output/07_resource')
```

**Chart Types:**

| Category | Charts |
|----------|--------|
| **Performance** | Normalized comparison (time/MB), Effect size forest plots |
| **Regression** | Overhead decomposition, Q-Q plots, Residual diagnostics |
| **Statistical** | Pairwise significance heatmaps (with corrections) |
| **Distribution** | Violin + box + strip, KDE, ECDF |
| **Resource** | Memory, CPU, I/O efficiency |

## Usage

### Quick Start

```python
from visualization import VisualizationConfig, ChartFactory
import pandas as pd

# Load data
data = pd.read_csv('benchmark_results.csv')

# Configure for paper
config = VisualizationConfig(mode='paper')
config.apply()

# Create charts
factory = ChartFactory(config)
factory.performance.create_normalized_performance_comparison(data, 'output/normalized_perf')
```

### Using the CLI Tool

```bash
# Run complete analysis
python benchmark/analyze_benchmark_scientific.py results.csv

# Custom output directory
python benchmark/analyze_benchmark_scientific.py results.csv -o analysis_output

# Presentation mode
python benchmark/analyze_benchmark_scientific.py results.csv --mode presentation

# Specify baseline strategy
python benchmark/analyze_benchmark_scientific.py results.csv --baseline "3.0_presidio"
```

## Critical Fixes from Previous Version

### ❌ Old (Incorrect)
```python
# Problem: Comparing raw execution time by file format
# Different formats have different file sizes!
pivot = data.pivot_table(
    values='wall_clock_time_sec',
    index='strategy',
    columns='file_extension',
    aggfunc='mean'
)
# This is scientifically invalid!
```

### ✅ New (Correct)
```python
# Solution: Normalize by file size
data['time_per_mb'] = data['wall_clock_time_sec'] / data['file_size_mb']

pivot = data.pivot_table(
    values='time_per_mb',  # Normalized metric
    index='strategy',
    columns='file_extension',
    aggfunc='mean'
)
# Now we can fairly compare across formats!
```

## Design Principles

### SOLID

1. **Single Responsibility**: Each class has one job
   - `VisualizationConfig`: Configuration only
   - `StatisticalAnalyzer`: Statistical tests only
   - `PerformanceCharts`: Performance visualizations only

2. **Open/Closed**: Extend without modifying
   - Add new chart types by creating new classes
   - Add new statistical tests by extending analyzers

3. **Liskov Substitution**: All charts inherit from `BaseChart`
   - Common interface: `create()`, `save()`

4. **Interface Segregation**: Focused factories
   - `PerformanceCharts`, `StatisticalCharts`, `RegressionCharts` are separate

5. **Dependency Inversion**: Depend on abstractions
   - Charts depend on `VisualizationConfig` interface, not concrete implementation

### DRY (Don't Repeat Yourself)

- Common configuration centralized in `VisualizationConfig`
- Statistical methods in reusable `StatisticalAnalyzer`
- Base chart template in `BaseChart` abstract class

### KISS (Keep It Simple, Stupid)

- Each function does one thing well
- Clear naming: `create_normalized_performance_comparison()` vs generic `plot()`
- Sensible defaults with optional customization

## Color Schemes

### Colorblind-Safe (Default)

Based on Wong (2011) palette, optimized for all types of colorblindness:

```python
WONG_BLUE      = '#0072B2'  # Primary
WONG_ORANGE    = '#E69F00'  # Secondary
WONG_GREEN     = '#009E73'  # Success
WONG_VERMILLION = '#D55E00' # Accent
WONG_SKY_BLUE  = '#56B4E9'  # Light
WONG_PURPLE    = '#CC79A7'  # Alternative
WONG_YELLOW    = '#F0E442'  # Highlight
WONG_BLACK     = '#000000'  # Text
```

## Figure Sizes

### IEEE Standards (Default)

```python
SINGLE_COLUMN  = (3.5, 2.625)  # inches
DOUBLE_COLUMN  = (7.0, 5.25)   # inches
```

### Nature/Science

```python
NATURE_SINGLE  = (89mm)  # ~3.5 inches
NATURE_DOUBLE  = (183mm) # ~7.2 inches
```

## Statistical Methods

### Effect Sizes

- **Cohen's d**: Standardized mean difference (0.2 = small, 0.5 = medium, 0.8 = large)
- **Hedges' g**: Bias-corrected for small samples (n < 20)
- **Rank-biserial r**: Effect size for Mann-Whitney U test

### Multiple Comparison Corrections

- **Bonferroni**: Conservative (family-wise error rate)
- **Holm**: Less conservative than Bonferroni
- **FDR (Benjamini-Hochberg)**: Controls false discovery rate (recommended)
- **FDR (Benjamini-Yekutieli)**: For dependent tests

### Normality Tests

- **Shapiro-Wilk**: Best for n < 5000
- **D'Agostino-Pearson**: Good for n > 20
- **Anderson-Darling**: Distribution-free

## Dependencies

```
numpy
pandas
matplotlib
seaborn
scipy
statsmodels  # For robust regression
```

Install all:
```bash
pip install numpy pandas matplotlib seaborn scipy statsmodels
```

## References

1. Wong, B. (2011). Points of view: Color blindness. *Nature Methods*, 8(6), 441.
2. Cohen, J. (1988). *Statistical power analysis for the behavioral sciences*. Routledge.
3. Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. *Journal of the Royal Statistical Society*, 57(1), 289-300.
4. Hedges, L. V., & Olkin, I. (1985). *Statistical methods for meta-analysis*. Academic Press.

## License

Copyright (c) 2026 AnonShield Team. All rights reserved.
