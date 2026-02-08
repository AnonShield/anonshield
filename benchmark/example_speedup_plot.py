#!/usr/bin/env python3
"""
Example: Create Speedup Comparison Plot (Like Your Example)

This demonstrates how to create publication-quality speedup plots
similar to the matplotlib code you showed, but using our scientific
visualization framework.

Features:
- Log scale time plot
- Throughput comparison
- Automatic speedup annotations
- Publication-ready styling
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add visualization module to path
sys.path.insert(0, str(Path(__file__).parent))

from visualization import VisualizationConfig, ChartFactory


def example_with_your_data():
    """Reproduce your exact example using our framework."""

    # Your data (from your code)
    data_dict = {
        'Size_MB': [0.25, 0.50, 1.00, 2.00],
        'v2.0_Default_Time': [211.55, 440.43, 871.07, 1908.79],
        'v3.0_Standalone_Time': [10.64, 14.53, 21.76, 32.05],
        'v3.0_Hybrid_Time': [18.89, 26.76, 41.81, np.nan]
    }

    # Convert to benchmark format
    rows = []
    for i, size in enumerate(data_dict['Size_MB']):
        # v2.0 Default
        rows.append({
            'version': '2.0',
            'strategy': 'default',
            'version_strategy': 'v2.0_Default',
            'file_size_mb': size,
            'file_size_kb': size * 1024,
            'wall_clock_time_sec': data_dict['v2.0_Default_Time'][i],
            'throughput_mb_per_sec': size / data_dict['v2.0_Default_Time'][i],
            'file_name': f'test_{size}MB.json',
            'file_extension': 'json',
            'status': 'SUCCESS'
        })

        # v3.0 Standalone
        rows.append({
            'version': '3.0',
            'strategy': 'standalone',
            'version_strategy': 'v3.0_Standalone',
            'file_size_mb': size,
            'file_size_kb': size * 1024,
            'wall_clock_time_sec': data_dict['v3.0_Standalone_Time'][i],
            'throughput_mb_per_sec': size / data_dict['v3.0_Standalone_Time'][i],
            'file_name': f'test_{size}MB.json',
            'file_extension': 'json',
            'status': 'SUCCESS'
        })

        # v3.0 Hybrid (skip NaN)
        if not np.isnan(data_dict['v3.0_Hybrid_Time'][i]):
            rows.append({
                'version': '3.0',
                'strategy': 'hybrid',
                'version_strategy': 'v3.0_Hybrid',
                'file_size_mb': size,
                'file_size_kb': size * 1024,
                'wall_clock_time_sec': data_dict['v3.0_Hybrid_Time'][i],
                'throughput_mb_per_sec': size / data_dict['v3.0_Hybrid_Time'][i],
                'file_name': f'test_{size}MB.json',
                'file_extension': 'json',
                'status': 'SUCCESS'
            })

    df = pd.DataFrame(rows)

    # Setup visualization
    config = VisualizationConfig(mode='paper')
    config.apply()
    factory = ChartFactory(config)

    # Generate speedup plot
    output_dir = Path('benchmark/results/speedup_example')
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🎨 Generating speedup comparison plot...")
    factory.scalability.create_speedup_comparison(
        df,
        baseline_strategy='v2.0_Default',
        output_path=str(output_dir / 'speedup_comparison')
    )

    print(f"✅ Saved to: {output_dir / 'speedup_comparison.png/pdf'}")
    print("\n📊 This plot shows:")
    print("   • Panel A: Time vs Size (log-log scale)")
    print("   • Panel B: Throughput vs Size")
    print("   • Automatic speedup annotations")
    print("   • Publication-ready styling (300 DPI)")

    # Calculate and display speedups
    print("\n📈 Speedups at 1.00 MB:")
    baseline_time = df[(df['version_strategy'] == 'v2.0_Default') &
                       (df['file_size_mb'] == 1.0)]['wall_clock_time_sec'].iloc[0]

    for strategy in ['v3.0_Standalone', 'v3.0_Hybrid']:
        strategy_data = df[(df['version_strategy'] == strategy) &
                          (df['file_size_mb'] == 1.0)]
        if len(strategy_data) > 0:
            strategy_time = strategy_data['wall_clock_time_sec'].iloc[0]
            speedup = baseline_time / strategy_time
            print(f"   {strategy}: {speedup:.1f}× faster than v2.0")


def example_with_real_benchmark_data():
    """Example using real benchmark results."""

    # Load your actual benchmark results
    results_file = Path('benchmark/orchestrated_results/full_benchmark_results.csv')

    if not results_file.exists():
        print(f"⚠️  File not found: {results_file}")
        print("   Run the benchmark first to generate data.")
        return

    print(f"📁 Loading data from: {results_file}")
    df = pd.read_csv(results_file)

    # Setup
    config = VisualizationConfig(mode='paper')
    config.apply()
    factory = ChartFactory(config)

    # Generate plot
    output_dir = Path('benchmark/results/speedup_example')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Choose baseline (first strategy alphabetically)
    baseline = sorted(df['version_strategy'].unique())[0]

    print(f"🎨 Generating speedup comparison (baseline: {baseline})...")
    factory.scalability.create_speedup_comparison(
        df,
        baseline_strategy=baseline,
        output_path=str(output_dir / 'speedup_real_data')
    )

    print(f"✅ Saved to: {output_dir / 'speedup_real_data.png/pdf'}")


def main():
    """Run examples."""
    print("=" * 80)
    print("🚀 SPEEDUP COMPARISON PLOT EXAMPLES")
    print("=" * 80)

    print("\n📊 Example 1: Using Your Data")
    print("-" * 80)
    example_with_your_data()

    print("\n" + "=" * 80)
    print("\n📊 Example 2: Using Real Benchmark Data")
    print("-" * 80)
    try:
        example_with_real_benchmark_data()
    except Exception as e:
        print(f"⚠️  Could not load real data: {e}")
        print("   This is normal if you haven't run benchmarks yet.")

    print("\n" + "=" * 80)
    print("✨ DONE!")
    print("=" * 80)
    print("\n💡 To use with your data:")
    print("   1. Format your data as shown in example_with_your_data()")
    print("   2. Call factory.scalability.create_speedup_comparison()")
    print("   3. Output: publication-ready PNG + PDF (300 DPI)")


if __name__ == '__main__':
    main()
