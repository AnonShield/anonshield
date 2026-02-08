#!/usr/bin/env python3
"""
Scientific Benchmark Analysis Tool - Publication Quality

Complete refactoring with SOLID principles and publication-ready visualizations.
Fixes critical issues and adds missing scientific analyses.

CRITICAL FIXES:
1. ✅ Removed raw "time by format" comparisons (replaced with normalized metrics)
2. ✅ Added overhead decomposition analysis
3. ✅ Added effect size calculations (Cohen's d)
4. ✅ Added multiple comparison corrections
5. ✅ Added regression diagnostics (Q-Q plots, residual analysis)
6. ✅ Added normality tests
7. ✅ Colorblind-safe palettes (Wong 2011)
8. ✅ Publication-standard figure sizes (IEEE format)

NEW VISUALIZATIONS:
- Normalized performance comparison (time per MB)
- Overhead decomposition with regression
- Effect size forest plots
- Pairwise significance heatmaps with corrections
- Q-Q plots for normality
- Advanced distribution analysis (violin + KDE + ECDF)
- Resource efficiency analysis

Author: AnonShield Team
Version: 3.0 - Scientific Refactoring
"""

import argparse
import sys
import warnings
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

# Add visualization module to path
sys.path.insert(0, str(Path(__file__).parent))

from visualization import (
    VisualizationConfig,
    ChartFactory,
    StatisticalAnalyzer,
    RegressionAnalyzer,
    EffectSizeCalculator,
)

warnings.filterwarnings('ignore')


class ScientificBenchmarkAnalyzer:
    """Main analyzer class orchestrating all analyses."""

    def __init__(self, csv_path: str, output_dir: str = "benchmark/results/scientific",
                 mode: str = 'paper'):
        """Initialize analyzer.

        Args:
            csv_path: Path to benchmark CSV/JSON results
            output_dir: Output directory for results
            mode: 'paper' (publication), 'presentation', or 'screen'
        """
        self.data_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize configuration
        self.config = VisualizationConfig(mode=mode)
        self.config.apply()

        # Initialize chart factory
        self.factory = ChartFactory(self.config)

        # Initialize analyzers
        self.stat_analyzer = StatisticalAnalyzer()
        self.reg_analyzer = RegressionAnalyzer()
        self.effect_calc = EffectSizeCalculator()

        # Load data
        print("=" * 80)
        print("🔬 SCIENTIFIC BENCHMARK ANALYSIS - Publication Quality")
        print("=" * 80)
        print(f"\n📁 Loading data from: {csv_path}")

        if self.data_path.suffix == '.json':
            self.df = pd.read_json(csv_path)
            print("   Format: JSON")
        elif self.data_path.suffix == '.csv':
            self.df = pd.read_csv(csv_path)
            print("   Format: CSV")
        else:
            raise ValueError(f"Unsupported format: {self.data_path.suffix}")

        # Preprocess data
        self._preprocess_data()

        print(f"\n✅ Loaded {len(self.df)} records")
        print(f"   Versions: {sorted(self.df['version'].unique())}")
        print(f"   Strategies: {sorted(self.df['strategy'].unique())}")
        print(f"   File types: {sorted(self.df['file_extension'].unique())}")
        print()

    def _preprocess_data(self):
        """Preprocess and validate data."""
        # Filter successful runs
        if 'status' in self.df.columns:
            initial_count = len(self.df)
            self.df = self.df[self.df['status'] == 'SUCCESS'].copy()
            failed_count = initial_count - len(self.df)
            if failed_count > 0:
                print(f"   ⚠️  Filtered out {failed_count} failed runs")

        # Create combined identifier
        if 'version' in self.df.columns and 'strategy' in self.df.columns:
            self.df['version_strategy'] = (
                self.df['version'].astype(str) + '_' + self.df['strategy']
            )

        # Clean file extensions and create file_type alias
        if 'file_extension' in self.df.columns:
            self.df['file_extension'] = (
                self.df['file_extension'].str.replace('.', '', regex=False)
                                        .str.replace('*', 'aggregate', regex=False)
            )
            # Create file_type as alias for file_extension (for consistency)
            if 'file_type' not in self.df.columns:
                self.df['file_type'] = self.df['file_extension']

        # Compute derived metrics
        if 'file_size_mb' in self.df.columns and 'wall_clock_time_sec' in self.df.columns:
            # Time per MB (normalized metric - CRITICAL FIX)
            self.df['time_per_mb'] = self.df['wall_clock_time_sec'] / self.df['file_size_mb'].replace(0, np.nan)

        # CPU efficiency
        if all(col in self.df.columns for col in ['user_time_sec', 'system_time_sec', 'wall_clock_time_sec']):
            cpu_time = self.df['user_time_sec'] + self.df['system_time_sec']
            self.df['cpu_efficiency'] = cpu_time / self.df['wall_clock_time_sec'].replace(0, np.nan)

        # I/O wait
        if 'io_wait_sec' not in self.df.columns and all(
            col in self.df.columns for col in ['wall_clock_time_sec', 'user_time_sec', 'system_time_sec']
        ):
            cpu_time = self.df['user_time_sec'].fillna(0) + self.df['system_time_sec'].fillna(0)
            wall_time = self.df['wall_clock_time_sec'].fillna(0)
            self.df['io_wait_sec'] = (wall_time - cpu_time).clip(lower=0.0)
            self.df['io_wait_percent'] = (
                self.df['io_wait_sec'] / self.df['wall_clock_time_sec'].replace(0, np.nan) * 100
            )

        print("   ✓ Data preprocessing complete")

    def run_complete_analysis(self, baseline_strategy: Optional[str] = None):
        """Run complete scientific analysis with all visualizations.

        Args:
            baseline_strategy: Reference strategy for effect size comparisons
                             (default: first strategy alphabetically)
        """
        print("\n" + "=" * 80)
        print("🚀 RUNNING COMPLETE SCIENTIFIC ANALYSIS")
        print("=" * 80)

        if baseline_strategy is None:
            baseline_strategy = sorted(self.df['version_strategy'].unique())[0]

        print(f"\n📊 Baseline strategy for comparisons: {baseline_strategy}\n")

        # First, run analysis with ALL formats combined
        print("\n" + "=" * 80)
        print("📊 PART 1: ALL FORMATS COMBINED")
        print("=" * 80)
        self._run_analysis_for_subset(self.df, baseline_strategy, self.output_dir, "all_formats")

        # Then, run separate analysis for each file format
        if 'file_type' in self.df.columns and self.df['file_type'].nunique() > 1:
            print("\n" + "=" * 80)
            print("📊 PART 2: ANALYSIS BY FILE FORMAT")
            print("=" * 80)

            file_formats = sorted(self.df['file_type'].unique())
            print(f"\n🗂️  Detected file formats: {', '.join(file_formats)}")

            for fmt in file_formats:
                print(f"\n{'─' * 80}")
                print(f"📄 Analyzing format: {fmt.upper()}")
                print(f"{'─' * 80}")

                # Filter data for this format
                format_data = self.df[self.df['file_type'] == fmt].copy()

                # Create subdirectory for this format
                format_dir = self.output_dir / "by_format" / fmt
                format_dir.mkdir(parents=True, exist_ok=True)

                # Run analysis for this format
                self._run_analysis_for_subset(format_data, baseline_strategy, format_dir, fmt)
        else:
            print("\n⚠️  Only one file format detected - skipping per-format analysis")

        print("\n" + "=" * 80)
        print("✨ COMPLETE ANALYSIS FINISHED!")
        print(f"📂 All outputs saved to: {self.output_dir}")
        print("=" * 80)

    def _run_analysis_for_subset(self, data: pd.DataFrame, baseline_strategy: str,
                                  output_dir: Path, subset_name: str):
        """Run complete analysis for a data subset (all formats or single format).

        Args:
            data: DataFrame subset to analyze
            baseline_strategy: Reference strategy for comparisons
            output_dir: Output directory for this subset
            subset_name: Name of the subset (for logging)
        """
        n_records = len(data)
        n_strategies = data['version_strategy'].nunique()

        print(f"\n📊 Analyzing {n_records} records, {n_strategies} strategies")

        # 1. Normalized Performance Comparison (CRITICAL FIX)
        print("1️⃣  Creating normalized performance comparison...")
        self.factory.performance.create_normalized_performance_comparison(
            data,
            str(output_dir / "01_normalized_performance")
        )
        print("   ✅ Saved: 01_normalized_performance.png/pdf")

        # 2. Effect Size Comparison
        print("\n2️⃣  Creating effect size comparison (Cohen's d)...")
        if n_strategies > 1:
            self.factory.performance.create_effect_size_comparison(
                data,
                baseline_strategy,
                str(output_dir / "02_effect_size_comparison")
            )
            print("   ✅ Saved: 02_effect_size_comparison.png/pdf")
        else:
            print("   ⚠️  Skipped: Requires multiple strategies for comparison")

        # 3. Overhead Decomposition
        print("\n3️⃣  Creating overhead decomposition analysis...")
        if data['file_size_mb'].nunique() > 1:
            self.factory.regression.create_overhead_decomposition(
                data,
                'version_strategy',
                str(output_dir / "03_overhead_decomposition")
            )
            print("   ✅ Saved: 03_overhead_decomposition.png/pdf")
        else:
            print("   ⚠️  Skipped: Requires variation in file sizes (only 1 size found)")

        # 4. Q-Q Normality Plots
        print("\n4️⃣  Creating Q-Q normality plots...")
        self.factory.regression.create_qq_normality_plots(
            data,
            'version_strategy',
            'wall_clock_time_sec',
            str(output_dir / "04_qq_normality_plots")
        )
        print("   ✅ Saved: 04_qq_normality_plots.png/pdf")

        # 5. Pairwise Significance Heatmap
        print("\n5️⃣  Creating pairwise significance heatmap...")
        if n_strategies > 1:
            self.factory.statistical.create_pairwise_significance_heatmap(
                data,
                'version_strategy',
                'wall_clock_time_sec',
                str(output_dir / "05_pairwise_significance"),
                correction_method='fdr_bh'
            )
            print("   ✅ Saved: 05_pairwise_significance.png/pdf")
        else:
            print("   ⚠️  Skipped: Requires multiple strategies for pairwise comparison")

        # 6. Advanced Distribution Analysis
        print("\n6️⃣  Creating advanced distribution analysis...")
        self.factory.distribution.create_advanced_distribution(
            data,
            'version_strategy',
            'wall_clock_time_sec',
            str(output_dir / "06_distribution_analysis")
        )
        print("   ✅ Saved: 06_distribution_analysis.png/pdf")

        # 7. Resource Efficiency Analysis
        print("\n7️⃣  Creating resource efficiency analysis...")
        self.factory.resource.create_resource_efficiency_analysis(
            data,
            'version_strategy',
            str(output_dir / "07_resource_efficiency")
        )
        print("   ✅ Saved: 07_resource_efficiency.png/pdf")

        # 8. Scaling and Complexity Analysis
        print("\n8️⃣  Creating scaling and complexity analysis...")
        if data['file_size_mb'].nunique() > 1:
            self.factory.scalability.create_scaling_analysis(
                data,
                'version_strategy',
                str(output_dir / "08_scaling_complexity")
            )
            print("   ✅ Saved: 08_scaling_complexity.png/pdf")
        else:
            print("   ⚠️  Skipped: Requires variation in file sizes (only 1 size found)")

        # 9. Polynomial vs Linear Comparison
        print("\n9️⃣  Creating polynomial model comparison...")
        if data['file_size_mb'].nunique() > 1:
            self.factory.scalability.create_polynomial_comparison(
                data,
                'version_strategy',
                str(output_dir / "09_polynomial_comparison")
            )
            print("   ✅ Saved: 09_polynomial_comparison.png/pdf")
        else:
            print("   ⚠️  Skipped: Requires variation in file sizes (only 1 size found)")

        # 10. Correlation Analysis
        print("\n🔟 Creating correlation analysis...")
        self.factory.correlation.create_correlation_heatmap(
            data,
            str(output_dir / "10_correlation_heatmap"),
            method='spearman'
        )
        print("   ✅ Saved: 10_correlation_heatmap.png/pdf")

        # 11. ANOVA/Kruskal-Wallis Analysis
        print("\n1️⃣1️⃣  Creating variance analysis (ANOVA)...")
        if n_strategies > 1:
            self.factory.variance.create_anova_summary(
                data,
                'version_strategy',
                str(output_dir / "11_variance_analysis"),
                metric='wall_clock_time_sec'
            )
            print("   ✅ Saved: 11_variance_analysis.png/pdf")
        else:
            print("   ⚠️  Skipped: Requires multiple strategies for variance analysis")

        # 13. Speedup Comparison (Time + Throughput)
        print("\n1️⃣3️⃣  Creating speedup comparison (log scale)...")
        if data['file_size_mb'].nunique() > 1 and n_strategies > 1:
            self.factory.scalability.create_speedup_comparison(
                data,
                baseline_strategy,
                str(output_dir / "13_speedup_comparison")
            )
            print("   ✅ Saved: 13_speedup_comparison.png/pdf")
        else:
            print("   ⚠️  Skipped: Requires variation in file sizes and multiple strategies")

        # 12. Generate statistical report
        print("\n1️⃣2️⃣  Generating statistical summary report...")
        self._generate_statistical_report_for_subset(data, output_dir, subset_name)
        print("   ✅ Saved: statistical_report.txt")

    def _generate_statistical_report_for_subset(self, data: pd.DataFrame,
                                                 output_dir: Path, subset_name: str):
        """Generate comprehensive statistical summary report for a data subset."""
        report = []
        report.append("=" * 80)
        report.append(f"STATISTICAL SUMMARY REPORT - {subset_name.upper()}")
        report.append("=" * 80)
        report.append("")

        # Dataset summary
        report.append("DATASET SUMMARY:")
        report.append("-" * 80)
        report.append(f"Total samples: {len(data)}")
        report.append(f"Strategies: {data['version_strategy'].nunique()}")
        if 'file_extension' in data.columns:
            report.append(f"File formats: {data['file_extension'].nunique()}")
        report.append("")

        # Normality tests
        report.append("NORMALITY TESTS (Shapiro-Wilk):")
        report.append("-" * 80)
        for strategy in sorted(data['version_strategy'].unique()):
            strat_data = data[data['version_strategy'] == strategy]['wall_clock_time_sec'].dropna().values
            if len(strat_data) > 2:
                result = self.stat_analyzer.test_normality(strat_data)
                is_normal = result.get('is_normal', False)
                status = "✓ Normal" if is_normal else "✗ Non-normal"

                if 'shapiro_wilk' in result:
                    p_val = result['shapiro_wilk']['p_value']
                    report.append(f"{strategy:30s} {status:12s} (p={p_val:.4f})")
                else:
                    report.append(f"{strategy:30s} {status}")
        report.append("")

        # Descriptive statistics
        report.append("DESCRIPTIVE STATISTICS (wall_clock_time_sec):")
        report.append("-" * 80)
        stats_df = data.groupby('version_strategy')['wall_clock_time_sec'].describe()
        report.append(stats_df.to_string())
        report.append("")

        # Performance rankings
        report.append("PERFORMANCE RANKINGS (by mean time per MB):")
        report.append("-" * 80)
        if 'time_per_mb' in data.columns:
            rankings = data.groupby('version_strategy')['time_per_mb'].mean().sort_values()
            for rank, (strategy, value) in enumerate(rankings.items(), 1):
                report.append(f"{rank}. {strategy:30s} {value:.4f} sec/MB")
        report.append("")

        # Save report
        report_path = output_dir / "statistical_report.txt"
        with open(report_path, 'w') as f:
            f.write('\n'.join(report))

    def _generate_statistical_report(self):
        """Generate comprehensive statistical summary report (legacy - for backwards compatibility)."""
        self._generate_statistical_report_for_subset(self.df, self.output_dir, "all_formats")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scientific Benchmark Analysis - Publication Quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard analysis (paper mode)
  python analyze_benchmark_scientific.py results.csv

  # Presentation mode (larger fonts)
  python analyze_benchmark_scientific.py results.csv --mode presentation

  # Custom baseline strategy
  python analyze_benchmark_scientific.py results.csv --baseline "3.0_presidio"

Output:
  All visualizations are saved in both PNG (300 DPI) and PDF formats.
  Figures use colorblind-safe palettes and publication-standard sizes.
        """
    )

    parser.add_argument(
        'csv_path',
        help='Path to benchmark results CSV or JSON file'
    )

    parser.add_argument(
        '-o', '--output-dir',
        default='benchmark/results/scientific',
        help='Output directory for analysis results (default: benchmark/results/scientific)'
    )

    parser.add_argument(
        '-m', '--mode',
        choices=['paper', 'presentation', 'screen'],
        default='paper',
        help='Output mode: paper (publication), presentation (slides), screen (display)'
    )

    parser.add_argument(
        '-b', '--baseline',
        help='Baseline strategy for effect size comparisons (default: first alphabetically)'
    )

    args = parser.parse_args()

    # Validate input file
    if not Path(args.csv_path).exists():
        print(f"❌ Error: File not found: {args.csv_path}")
        sys.exit(1)

    # Run analysis
    try:
        analyzer = ScientificBenchmarkAnalyzer(
            args.csv_path,
            args.output_dir,
            mode=args.mode
        )

        analyzer.run_complete_analysis(baseline_strategy=args.baseline)

    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
