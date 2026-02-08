#!/usr/bin/env python3
"""
Test script for scientific visualization module.
Generates sample data and creates all visualizations.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add visualization module to path
sys.path.insert(0, str(Path(__file__).parent))

from visualization import VisualizationConfig, ChartFactory


def generate_sample_data(n_samples: int = 100) -> pd.DataFrame:
    """Generate synthetic benchmark data for testing."""
    np.random.seed(42)

    strategies = ['1.0_default', '2.0_default', '3.0_presidio', '3.0_filtered', '3.0_hybrid']
    formats = ['txt', 'pdf', 'docx', 'csv', 'json', 'xml']

    data = []
    for strategy in strategies:
        for fmt in formats:
            n = n_samples // (len(strategies) * len(formats))

            # Generate realistic file sizes (0.1 MB to 50 MB)
            sizes_mb = np.random.lognormal(mean=1, sigma=1.5, size=n).clip(0.1, 50)

            # Strategy-specific base rates
            if 'presidio' in strategy:
                base_throughput = 0.05  # Slower
                base_overhead = 75
            elif 'filtered' in strategy:
                base_throughput = 0.15  # Faster
                base_overhead = 60
            elif 'hybrid' in strategy:
                base_throughput = 0.20  # Fastest
                base_overhead = 55
            else:
                base_throughput = 0.10  # Default
                base_overhead = 50

            # Add format-specific noise
            format_factor = {'txt': 1.0, 'pdf': 0.8, 'docx': 0.7, 'csv': 1.2,
                           'json': 1.1, 'xml': 0.9}.get(fmt, 1.0)

            throughput = base_throughput * format_factor * np.random.normal(1.0, 0.1, n)
            overhead = base_overhead * np.random.normal(1.0, 0.05, n)

            # Model: time = overhead + size / throughput
            times = overhead + (sizes_mb * 1024) / (throughput + 1e-6)  # Convert MB to KB

            # Memory usage (correlated with file size)
            memory_mb = 500 + sizes_mb * 20 + np.random.normal(0, 100, n)

            # CPU metrics
            user_time = times * 0.7 * np.random.normal(1.0, 0.1, n)
            system_time = times * 0.15 * np.random.normal(1.0, 0.2, n)
            io_wait = times - user_time - system_time
            io_wait = np.maximum(io_wait, 0)

            for i in range(n):
                data.append({
                    'version': strategy.split('_')[0],
                    'strategy': '_'.join(strategy.split('_')[1:]),
                    'version_strategy': strategy,
                    'file_extension': fmt,
                    'file_name': f'test_{fmt}_{i}.{fmt}',
                    'file_size_mb': sizes_mb[i],
                    'file_size_kb': sizes_mb[i] * 1024,
                    'wall_clock_time_sec': times[i],
                    'user_time_sec': user_time[i],
                    'system_time_sec': system_time[i],
                    'io_wait_sec': io_wait[i],
                    'peak_memory_mb': memory_mb[i],
                    'max_resident_set_kb': memory_mb[i] * 1024,
                    'cpu_percent': ((user_time[i] + system_time[i]) / times[i] * 100),
                    'throughput_mb_per_sec': sizes_mb[i] / times[i],
                    'status': 'SUCCESS',
                    'run_number': i % 3 + 1,
                })

    return pd.DataFrame(data)


def main():
    """Run test."""
    print("=" * 80)
    print("🧪 TESTING SCIENTIFIC VISUALIZATION MODULE")
    print("=" * 80)

    # Generate sample data
    print("\n1️⃣  Generating synthetic benchmark data...")
    df = generate_sample_data(n_samples=300)
    print(f"   ✅ Generated {len(df)} samples")
    print(f"   Strategies: {df['version_strategy'].unique()}")
    print(f"   Formats: {df['file_extension'].unique()}")

    # Save sample data
    output_dir = Path('benchmark/results/test_scientific')
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_dir / 'sample_data.csv', index=False)
    print(f"   💾 Saved to: {output_dir / 'sample_data.csv'}")

    # Initialize configuration
    print("\n2️⃣  Initializing visualization config (paper mode)...")
    config = VisualizationConfig(mode='paper')
    config.apply()
    print("   ✅ Configuration applied")

    # Create factory
    print("\n3️⃣  Creating chart factory...")
    factory = ChartFactory(config)
    print("   ✅ Factory initialized")

    # Test each chart type
    print("\n4️⃣  Generating test visualizations...")

    try:
        print("   📊 Normalized performance comparison...")
        factory.performance.create_normalized_performance_comparison(
            df, str(output_dir / '01_normalized_performance')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Effect size comparison...")
        factory.performance.create_effect_size_comparison(
            df, '3.0_presidio', str(output_dir / '02_effect_size')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Overhead decomposition...")
        factory.regression.create_overhead_decomposition(
            df, 'version_strategy', str(output_dir / '03_overhead')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Q-Q normality plots...")
        factory.regression.create_qq_normality_plots(
            df, 'version_strategy', 'wall_clock_time_sec',
            str(output_dir / '04_qq_plots')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Pairwise significance heatmap...")
        factory.statistical.create_pairwise_significance_heatmap(
            df, 'version_strategy', 'wall_clock_time_sec', 'fdr_bh',
            str(output_dir / '05_pairwise')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Distribution analysis...")
        factory.distribution.create_advanced_distribution(
            df, 'version_strategy', 'wall_clock_time_sec',
            str(output_dir / '06_distribution')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Resource efficiency analysis...")
        factory.resource.create_resource_efficiency_analysis(
            df, 'version_strategy', str(output_dir / '07_resource')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Scaling and complexity analysis...")
        factory.scalability.create_scaling_analysis(
            df, 'version_strategy', str(output_dir / '08_scaling')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Polynomial model comparison...")
        factory.scalability.create_polynomial_comparison(
            df, 'version_strategy', str(output_dir / '09_polynomial')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 Correlation heatmap...")
        factory.correlation.create_correlation_heatmap(
            df, str(output_dir / '10_correlation'), method='spearman'
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    try:
        print("   📊 ANOVA/Kruskal-Wallis analysis...")
        factory.variance.create_anova_summary(
            df, 'version_strategy', str(output_dir / '11_anova')
        )
        print("      ✅ Success")
    except Exception as e:
        print(f"      ❌ Failed: {e}")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE!")
    print(f"📂 All test outputs saved to: {output_dir}")
    print("\n📊 GENERATED TEST VISUALIZATIONS (11 total):")
    print("   1-7. Core analyses (performance, effect size, overhead, etc.)")
    print("   8. Scaling & complexity (log-log plots)")
    print("   9. Polynomial comparison (linear vs quadratic)")
    print("   10. Correlation heatmap (with significance)")
    print("   11. ANOVA & Kruskal-Wallis")
    print("=" * 80)


if __name__ == '__main__':
    main()
