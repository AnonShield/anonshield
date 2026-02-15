#!/usr/bin/env python3
"""
Chart Generation Module - Factory Pattern

Publication-quality charts for scientific papers.
Each chart class is responsible for one type of visualization.

Author: AnonShield Team
Version: 3.0
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import seaborn as sns
from scipy import stats

from .config import VisualizationConfig
from .statistics import (
    StatisticalAnalyzer,
    RegressionAnalyzer,
    EffectSizeCalculator,
)


class LayoutHelper:
    """Helper class for improving chart layouts and preventing label overlap."""

    @staticmethod
    def rotate_xlabels(ax, rotation=45, ha='right'):
        """Rotate x-axis labels to prevent overlap."""
        for label in ax.get_xticklabels():
            label.set_rotation(rotation)
            label.set_ha(ha)

    @staticmethod
    def rotate_ylabels(ax, rotation=0, ha='right'):
        """Rotate y-axis labels if needed."""
        for label in ax.get_yticklabels():
            label.set_rotation(rotation)
            label.set_ha(ha)

    @staticmethod
    def adjust_heatmap_size(n_rows, n_cols, base_size=0.5, min_size=8, max_size=20):
        """Calculate appropriate figure size for heatmap based on elements.

        Args:
            n_rows: Number of rows in heatmap
            n_cols: Number of columns in heatmap
            base_size: Size per cell in inches
            min_size: Minimum dimension
            max_size: Maximum dimension

        Returns:
            Tuple of (width, height) in inches
        """
        width = max(min_size, min(max_size, n_cols * base_size + 2))
        height = max(min_size, min(max_size, n_rows * base_size + 2))
        return (width, height)

    @staticmethod
    def smart_tick_spacing(ax, axis='x', max_ticks=10):
        """Reduce tick density if too many ticks."""
        if axis == 'x':
            ticks = ax.get_xticks()
            labels = ax.get_xticklabels()
        else:
            ticks = ax.get_yticks()
            labels = ax.get_yticklabels()

        if len(ticks) > max_ticks:
            # Keep every Nth tick
            step = len(ticks) // max_ticks + 1
            if axis == 'x':
                ax.set_xticks(ticks[::step])
            else:
                ax.set_yticks(ticks[::step])

    @staticmethod
    def improve_legend_placement(ax, ncol=None, loc='best', fontsize=None):
        """Improve legend placement to avoid overlap with data."""
        legend = ax.get_legend()
        if legend is None:
            return

        # Calculate number of columns based on number of entries
        if ncol is None:
            n_entries = len(legend.get_texts())
            ncol = min(3, max(1, n_entries // 4))

        # Recreate legend with better parameters
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc=loc, ncol=ncol,
                 fontsize=fontsize, framealpha=0.9,
                 edgecolor='gray', fancybox=True)

    @staticmethod
    def apply_tight_layout(fig, pad=1.5):
        """Apply tight layout with generous padding."""
        try:
            fig.tight_layout(pad=pad)
        except:
            # Fallback to manual adjustment
            fig.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)


class BaseChart(ABC):
    """Abstract base class for all charts (Template Method pattern)."""

    def __init__(self, config: VisualizationConfig):
        """Initialize chart with configuration.

        Args:
            config: VisualizationConfig instance
        """
        self.config = config
        self.fig = None
        self.axes = None

    @abstractmethod
    def create(self, data: pd.DataFrame, **kwargs) -> plt.Figure:
        """Create the chart. Must be implemented by subclasses.

        Args:
            data: DataFrame with benchmark data
            **kwargs: Additional parameters

        Returns:
            Matplotlib Figure object
        """
        pass

    def save(self, filepath: str, dpi: Optional[int] = None):
        """Save figure to file.

        Args:
            filepath: Output path
            dpi: Resolution (None = use config default)
        """
        if self.fig is None:
            raise ValueError("No figure to save. Call create() first.")
        self.config.save_figure(self.fig, filepath, dpi)

    def _add_significance_stars(self, ax, x1: float, x2: float, y: float,
                               p_value: float, height_offset: float = 0.05):
        """Add significance stars between two bars.

        Args:
            ax: Axes object
            x1, x2: X positions of bars
            y: Y position for the line
            p_value: P-value to determine stars
            height_offset: Vertical offset for text
        """
        # Determine stars
        if p_value < 0.0001:
            stars = '****'
        elif p_value < 0.001:
            stars = '***'
        elif p_value < 0.01:
            stars = '**'
        elif p_value < 0.05:
            stars = '*'
        else:
            stars = 'ns'

        # Draw line
        ax.plot([x1, x1, x2, x2], [y, y + height_offset, y + height_offset, y],
               'k-', linewidth=1)

        # Add text
        ax.text((x1 + x2) / 2, y + height_offset, stars,
               ha='center', va='bottom',
               fontsize=self.config.typography.SIZE_ANNOTATION,
               fontweight='bold')


class PerformanceCharts:
    """Factory for performance-related charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.stat_analyzer = StatisticalAnalyzer()
        self.effect_calc = EffectSizeCalculator()

    def create_normalized_performance_comparison(self, data: pd.DataFrame,
                                                 output_path: str):
        """Create normalized performance comparison (time per MB).

        CRITICAL FIX: This replaces the flawed "time by format" charts.
        Normalizes execution time by file size to enable fair comparisons.

        Args:
            data: Benchmark DataFrame
            output_path: Save path
        """
        # Compute normalized metric: seconds per MB
        data_clean = data[data['file_size_mb'] > 0].copy()
        data_clean['time_per_mb'] = (
            data_clean['wall_clock_time_sec'] / data_clean['file_size_mb']
        )

        # Also compute throughput for validation (should be inverse)
        # Using KB/s for better readability
        data_clean['throughput_kb_per_sec'] = (
            data_clean['file_size_mb'] * 1024 / data_clean['wall_clock_time_sec']
        )

        # Sort strategies by version (1.0, 2.0, 3.0, ...) for consistent grouping
        strategies = self.config.sort_strategies_by_version(
            list(data_clean['version_strategy'].unique())
        )
        formats = sorted(data_clean['file_extension'].unique())
        n_strategies = len(strategies)
        n_formats = len(formats)

        # Adjust figure size based on data complexity
        base_width = max(12, 4 * 3)  # 3 panels, at least 4" each
        base_height = max(8, n_strategies * 0.4 + 2)  # Dynamic height based on strategies
        fig = plt.figure(figsize=(base_width, base_height))
        gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35, hspace=0.3)

        # Use consistent colors for version+strategy across all charts
        colors = self.config.get_colors(n_strategies, strategies)

        # Panel A: Time per MB by strategy
        ax1 = fig.add_subplot(gs[0, 0])
        strategy_stats = data_clean.groupby('version_strategy').agg({
            'time_per_mb': ['mean', 'std']
        })
        strategy_stats.columns = ['mean', 'std']
        # Keep order by version (1.0, 2.0, 3.0) instead of sorting by value
        strategy_stats = strategy_stats.reindex(strategies)

        x_pos = np.arange(len(strategy_stats))
        bars = ax1.barh(x_pos, strategy_stats['mean'], xerr=strategy_stats['std'],
                       color=colors, edgecolor='black', linewidth=0.8,
                       capsize=4, error_kw={'linewidth': 1.5})

        ax1.set_yticks(x_pos)
        # Truncate long labels if needed
        labels = [s[:25] + '...' if len(s) > 25 else s for s in strategy_stats.index]
        ax1.set_yticklabels(labels, fontsize=self.config.typography.SIZE_AXIS_TICK)
        ax1.set_xlabel('Time per MB (sec/MB)', fontweight='bold',
                      fontsize=self.config.typography.SIZE_AXIS_LABEL)
        ax1.set_title('(A) Normalized Execution Time', fontweight='bold', pad=10)
        ax1.grid(axis='x', alpha=0.3)

        # Add value labels (only if not too crowded)
        if n_strategies <= 8:
            for i, (mean, std) in enumerate(zip(strategy_stats['mean'], strategy_stats['std'])):
                # Use dynamic offset
                offset = max(std * 0.1, mean * 0.05)
                ax1.text(mean + std + offset, i, f'{mean:.2f}',
                        va='center', fontsize=self.config.typography.SIZE_ANNOTATION)

        # Panel B: Throughput by strategy (inverse validation)
        ax2 = fig.add_subplot(gs[0, 1])
        throughput_stats = data_clean.groupby('version_strategy').agg({
            'throughput_kb_per_sec': ['mean', 'std']
        })
        throughput_stats.columns = ['mean', 'std']
        # Keep order by version (1.0, 2.0, 3.0) instead of sorting by value
        throughput_stats = throughput_stats.reindex(strategies)

        x_pos2 = np.arange(len(throughput_stats))
        bars2 = ax2.barh(x_pos2, throughput_stats['mean'], xerr=throughput_stats['std'],
                        color=colors, edgecolor='black', linewidth=0.8,
                        capsize=4, error_kw={'linewidth': 1.5})

        ax2.set_yticks(x_pos2)
        labels2 = [s[:25] + '...' if len(s) > 25 else s for s in throughput_stats.index]
        ax2.set_yticklabels(labels2, fontsize=self.config.typography.SIZE_AXIS_TICK)
        ax2.set_xlabel('Throughput (KB/sec)', fontweight='bold',
                      fontsize=self.config.typography.SIZE_AXIS_LABEL)
        ax2.set_title('(B) Processing Throughput', fontweight='bold', pad=10)
        ax2.grid(axis='x', alpha=0.3)

        # Add value labels (only if not too crowded)
        if n_strategies <= 8:
            for i, (mean, std) in enumerate(zip(throughput_stats['mean'], throughput_stats['std'])):
                offset = max(std * 0.1, mean * 0.05)
                ax2.text(mean + std + offset, i, f'{mean:.3f}',
                        va='center', fontsize=self.config.typography.SIZE_ANNOTATION)

        # Panel C: Heatmap - Time per MB by strategy × format
        ax3 = fig.add_subplot(gs[0, 2])
        pivot = data_clean.pivot_table(
            values='time_per_mb',
            index='version_strategy',
            columns='file_extension',
            aggfunc='mean'
        )
        # Keep order by version (1.0, 2.0, 3.0) in heatmap rows
        pivot = pivot.reindex(strategies)

        # Adjust annotation based on matrix size
        show_annot = (n_strategies * n_formats) <= 40  # Only annotate if not too dense
        annot_fontsize = max(6, 10 - n_formats // 2)  # Smaller font for more columns

        sns.heatmap(pivot, annot=show_annot, fmt='.2f', cmap='YlOrRd',
                   cbar_kws={'label': 'sec/MB'}, ax=ax3, linewidths=0.5,
                   linecolor='white', annot_kws={'fontsize': annot_fontsize})
        ax3.set_title('(C) Time per MB Matrix', fontweight='bold', pad=10)
        ax3.set_xlabel('File Format', fontweight='bold',
                      fontsize=self.config.typography.SIZE_AXIS_LABEL)
        ax3.set_ylabel('Strategy', fontweight='bold',
                      fontsize=self.config.typography.SIZE_AXIS_LABEL)

        # Rotate x labels if many formats
        if n_formats > 3:
            LayoutHelper.rotate_xlabels(ax3, rotation=45, ha='right')

        plt.suptitle('Normalized Performance Comparison (Size-Adjusted)',
                    fontsize=self.config.typography.SIZE_TITLE + 2,
                    fontweight='bold', y=0.98)

        LayoutHelper.apply_tight_layout(fig, pad=2.0)
        self.config.save_figure(fig, output_path)
        return fig

    def create_effect_size_comparison(self, data: pd.DataFrame,
                                     baseline_strategy: str,
                                     output_path: str):
        """Create forest plot showing effect sizes vs baseline.

        Args:
            data: Benchmark DataFrame
            baseline_strategy: Reference strategy for comparison
            output_path: Save path
        """
        fig, ax = plt.subplots(figsize=self.config.get_figure_size('single_tall'))

        # Sort by version for consistent grouping
        strategies = self.config.sort_strategies_by_version([
            s for s in data['version_strategy'].unique() if s != baseline_strategy
        ])

        baseline_data = data[data['version_strategy'] == baseline_strategy]['wall_clock_time_sec'].values

        effect_sizes = []
        for strategy in strategies:
            strategy_data = data[data['version_strategy'] == strategy]['wall_clock_time_sec'].values

            if len(strategy_data) > 1 and len(baseline_data) > 1:
                es = self.effect_calc.cohens_d(strategy_data, baseline_data)
                effect_sizes.append({
                    'strategy': strategy,
                    'effect_size': es.value,
                    'ci_lower': es.ci_lower,
                    'ci_upper': es.ci_upper,
                    'interpretation': es.interpretation
                })

        # Create DataFrame for plotting
        es_df = pd.DataFrame(effect_sizes)

        # Check if we have any effect sizes to plot
        if es_df.empty:
            # Create empty plot with message
            ax.text(0.5, 0.5, 'Insufficient data for effect size comparison\n(requires multiple samples per strategy)',
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=self.config.typography.SIZE_MEDIUM, style='italic')
            ax.set_xlabel("Cohen's d (Effect Size)", fontweight='bold')
            ax.set_title(f"Effect Size Comparison vs {baseline_strategy}",
                        fontweight='bold', pad=15)
            plt.tight_layout()
            self.config.save_figure(fig, output_path)
            return fig

        es_df = es_df.sort_values('effect_size')

        # Plot
        y_pos = np.arange(len(es_df))

        # Error bars (CI)
        errors = np.array([
            es_df['effect_size'] - es_df['ci_lower'],
            es_df['ci_upper'] - es_df['effect_size']
        ])

        # Plot each point individually with appropriate color
        for idx, row in es_df.iterrows():
            pos = np.where(es_df.index == idx)[0][0]
            color = self.config.colors.PRIMARY if row['effect_size'] < 0 else self.config.colors.ACCENT

            ax.errorbar(row['effect_size'], pos,
                       xerr=[[row['effect_size'] - row['ci_lower']],
                             [row['ci_upper'] - row['effect_size']]],
                       fmt='o', markersize=8, capsize=5, capthick=2,
                       color=color, ecolor='gray', linewidth=2)

        # Reference line at 0
        ax.axvline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.5)

        # Effect size regions
        ax.axvspan(-0.2, 0.2, alpha=0.1, color='gray', label='Negligible')
        ax.axvspan(-0.5, -0.2, alpha=0.1, color='green', label='Small')
        ax.axvspan(0.2, 0.5, alpha=0.1, color='orange')
        ax.axvspan(-0.8, -0.5, alpha=0.1, color='blue', label='Medium')
        ax.axvspan(0.5, 0.8, alpha=0.1, color='red')

        ax.set_yticks(y_pos)
        ax.set_yticklabels(es_df['strategy'])
        ax.set_xlabel("Cohen's d (Effect Size)", fontweight='bold')
        ax.set_title(f"Effect Size Comparison vs {baseline_strategy}",
                    fontweight='bold', pad=15)
        ax.grid(axis='x', alpha=0.3)

        # Add interpretation labels
        for i, row in es_df.iterrows():
            idx = np.where(es_df.index == i)[0][0]
            ax.text(row['ci_upper'] + 0.1, idx, row['interpretation'],
                   va='center', fontsize=self.config.typography.SIZE_ANNOTATION,
                   style='italic')

        # Legend
        ax.legend(loc='lower right', fontsize=self.config.typography.SIZE_LEGEND)

        plt.tight_layout()
        self.config.save_figure(fig, output_path)
        return fig


class RegressionCharts:
    """Factory for regression and overhead analysis charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.reg_analyzer = RegressionAnalyzer()

    def create_overhead_decomposition(self, data: pd.DataFrame,
                                     group_by: str, output_path: str,
                                     overhead_data: pd.DataFrame = None):
        """Create overhead decomposition analysis.

        Model: time = overhead + size/throughput
        Shows overhead and throughput components for each strategy.

        Args:
            data: Benchmark data
            group_by: Column to group by (e.g., 'version_strategy')
            output_path: Path to save output (without extension)
            overhead_data: Optional DataFrame with real overhead measurements

        Args:
            data: Benchmark DataFrame
            group_by: Column to group by (usually 'version_strategy')
            output_path: Save path
        """
        fig = plt.figure(figsize=self.config.get_figure_size('double_tall'))
        gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

        # Sort by version for consistent grouping
        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        colors = self.config.get_colors(len(groups), groups)

        overhead_results = []

        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group]

            # Filter valid data
            valid = (group_data['file_size_kb'] > 0) & (group_data['wall_clock_time_sec'] > 0)
            sizes = group_data.loc[valid, 'file_size_kb'].values
            times = group_data.loc[valid, 'wall_clock_time_sec'].values

            if len(sizes) < 3:
                continue

            # Check if we have real overhead data first
            use_real_overhead = False
            overhead_sec = None
            overhead_ci_lower = None
            overhead_ci_upper = None
            throughput_kbps = None
            
            if overhead_data is not None:
                # Try to find matching overhead from calibration data
                # Match by version and strategy from group name (e.g., "3.0_standalone")
                if '_' in group:
                    parts = group.split('_', 1)
                    if len(parts) == 2:
                        version, strategy = parts
                        overhead_match = overhead_data[
                            (overhead_data['version'].astype(str) == version) &
                            (overhead_data['strategy'] == strategy)
                        ]
                        if not overhead_match.empty:
                            # Use REAL overhead from calibration data
                            overhead_sec = overhead_match['wall_clock_time_sec'].mean()
                            overhead_std = overhead_match['wall_clock_time_sec'].std()
                            overhead_ci_lower = overhead_sec - overhead_std
                            overhead_ci_upper = overhead_sec + overhead_std
                            use_real_overhead = True
                            
                            # Calculate throughput based on real overhead
                            # throughput = size / (time - overhead)
                            processing_times = times - overhead_sec
                            processing_times = processing_times[processing_times > 0]  # Filter valid
                            if len(processing_times) > 0:
                                throughputs = sizes[times - overhead_sec > 0] / processing_times
                                throughput_kbps = np.mean(throughputs)
                            else:
                                # Fallback to regression if calculation fails
                                use_real_overhead = False
            
            # If no real overhead data, use regression model
            if not use_real_overhead:
                model = self.reg_analyzer.overhead_model(sizes, times, method='linear')
                overhead_sec = model.overhead_sec
                overhead_ci_lower = model.overhead_ci[0]
                overhead_ci_upper = model.overhead_ci[1]
                throughput_kbps = model.throughput_kb_per_sec
                r_squared = model.r_squared
            else:
                # Calculate R² for real overhead model
                predicted = overhead_sec + sizes / throughput_kbps
                ss_res = np.sum((times - predicted) ** 2)
                ss_tot = np.sum((times - np.mean(times)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            overhead_results.append({
                'group': group,
                'overhead_sec': overhead_sec,
                'throughput_kbps': throughput_kbps,
                'r_squared': r_squared,
                'overhead_ci_lower': overhead_ci_lower,
                'overhead_ci_upper': overhead_ci_upper,
                'sizes': sizes,
                'times': times,
                'predicted': overhead_sec + sizes / throughput_kbps,
                'residuals': times - (overhead_sec + sizes / throughput_kbps),
                'source': 'calibration' if use_real_overhead else 'regression'
            })

        # Panel A: Overhead bar chart
        ax1 = fig.add_subplot(gs[0, 0])
        overheads = [r['overhead_sec'] for r in overhead_results]
        overhead_errs = [(r['overhead_ci_upper'] - r['overhead_ci_lower']) / 2
                        for r in overhead_results]
        group_labels = [r['group'] for r in overhead_results]

        x_pos = np.arange(len(group_labels))
        ax1.bar(x_pos, overheads, yerr=overhead_errs, color=colors[:len(group_labels)],
               edgecolor='black', linewidth=0.8, capsize=4, error_kw={'linewidth': 1.5})
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(group_labels, rotation=45, ha='right')
        ax1.set_ylabel('Overhead (seconds)', fontweight='bold')
        ax1.set_title('(A) Fixed Overhead by Strategy', fontweight='bold', pad=10)
        ax1.grid(axis='y', alpha=0.3)

        # Add value labels
        for i, (oh, err) in enumerate(zip(overheads, overhead_errs)):
            ax1.text(i, oh + err + 1, f'{oh:.1f}±{err:.1f}s',
                    ha='center', fontsize=self.config.typography.SIZE_ANNOTATION)
        
        # Add source indicator
        sources = [r['source'] for r in overhead_results]
        if any(s == 'calibration' for s in sources):
            # Add legend to indicate data source
            from matplotlib.patches import Patch
            legend_elements = []
            if 'calibration' in sources:
                legend_elements.append(Patch(facecolor='lightgreen', edgecolor='black', 
                                            label='Real overhead (calibration)'))
            if 'regression' in sources:
                legend_elements.append(Patch(facecolor='lightcoral', edgecolor='black',
                                            label='Estimated (regression)'))
            
            # Color bars based on source
            for i, source in enumerate(sources):
                if source == 'calibration':
                    ax1.patches[i].set_facecolor('lightgreen')
                else:
                    ax1.patches[i].set_facecolor('lightcoral')
            
            ax1.legend(handles=legend_elements, loc='upper left', fontsize=8)

        # Panel B: Throughput bar chart
        ax2 = fig.add_subplot(gs[0, 1])
        throughputs = [r['throughput_kbps'] for r in overhead_results]
        ax2.bar(x_pos, throughputs, color=colors[:len(group_labels)],
               edgecolor='black', linewidth=0.8)
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(group_labels, rotation=45, ha='right')
        ax2.set_ylabel('Throughput (KB/sec)', fontweight='bold')
        ax2.set_title('(B) Processing Throughput', fontweight='bold', pad=10)
        ax2.grid(axis='y', alpha=0.3)

        # Add value labels
        for i, tp in enumerate(throughputs):
            ax2.text(i, tp + max(throughputs) * 0.02, f'{tp:.2f}',
                    ha='center', fontsize=self.config.typography.SIZE_ANNOTATION)

        # Panel C-D: Scatter with regression fits (first 2 groups)
        for plot_idx in range(min(2, len(overhead_results))):
            ax = fig.add_subplot(gs[1, plot_idx])
            result = overhead_results[plot_idx]

            # Scatter
            ax.scatter(result['sizes'], result['times'], alpha=0.6,
                      s=30, color=colors[plot_idx], edgecolors='black', linewidth=0.5)

            # Regression line
            sizes_sorted = np.sort(result['sizes'])
            predicted_sorted = result['overhead_sec'] + sizes_sorted / result['throughput_kbps']
            ax.plot(sizes_sorted, predicted_sorted, 'r--', linewidth=2,
                   label=f'Fit: R²={result["r_squared"]:.3f}')

            ax.set_xlabel('File Size (KB)', fontweight='bold')
            ax.set_ylabel('Execution Time (sec)', fontweight='bold')
            ax.set_title(f'({chr(67+plot_idx)}) {result["group"]}', fontweight='bold', pad=10)
            ax.legend(loc='upper left', fontsize=self.config.typography.SIZE_LEGEND)
            ax.grid(alpha=0.3)

            # Add model equation
            eq_text = f't = {result["overhead_sec"]:.1f} + size/{result["throughput_kbps"]:.2f}'
            ax.text(0.98, 0.05, eq_text, transform=ax.transAxes,
                   ha='right', va='bottom', fontsize=self.config.typography.SIZE_ANNOTATION,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Panel E-F: Residual plots (first 2 groups)
        for plot_idx in range(min(2, len(overhead_results))):
            ax = fig.add_subplot(gs[2, plot_idx])
            result = overhead_results[plot_idx]

            # Residual vs fitted
            ax.scatter(result['predicted'], result['residuals'], alpha=0.6,
                      s=30, color=colors[plot_idx], edgecolors='black', linewidth=0.5)
            ax.axhline(0, color='red', linestyle='--', linewidth=1.5)

            ax.set_xlabel('Fitted Values (sec)', fontweight='bold')
            ax.set_ylabel('Residuals (sec)', fontweight='bold')
            ax.set_title(f'({chr(69+plot_idx)}) Residual Diagnostic', fontweight='bold', pad=10)
            ax.grid(alpha=0.3)

            # Add statistics
            resid_mean = np.mean(result['residuals'])
            resid_std = np.std(result['residuals'], ddof=1)
            stats_text = f'μ={resid_mean:.2f}, σ={resid_std:.2f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                   ha='left', va='top', fontsize=self.config.typography.SIZE_ANNOTATION,
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

        plt.suptitle('Overhead Decomposition Analysis: time = overhead + size/throughput',
                    fontsize=self.config.typography.SIZE_TITLE + 2,
                    fontweight='bold', y=0.995)

        self.config.save_figure(fig, output_path)
        return fig

    def create_qq_normality_plots(self, data: pd.DataFrame,
                                  group_by: str, metric: str,
                                  output_path: str):
        """Create Q-Q plots for normality assessment.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            metric: Metric to test (e.g., 'wall_clock_time_sec')
            output_path: Save path
        """
        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        n_groups = len(groups)

        # Create grid
        ncols = min(3, n_groups)
        nrows = (n_groups + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols,
                                figsize=self.config.get_figure_size('double_square'))

        if n_groups == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        stat_analyzer = StatisticalAnalyzer()

        for idx, group in enumerate(groups):
            ax = axes[idx]
            group_data = data[data[group_by] == group][metric].dropna().values

            if len(group_data) < 3:
                ax.text(0.5, 0.5, f'{group}\nInsufficient data',
                       ha='center', va='center', transform=ax.transAxes)
                continue

            # Q-Q plot
            stats.probplot(group_data, dist="norm", plot=ax)

            # Normality test
            normality_result = stat_analyzer.test_normality(group_data)

            # Title with test result
            is_normal = normality_result.get('is_normal', False)
            normality_status = '✓ Normal' if is_normal else '✗ Non-normal'

            ax.set_title(f'{group}\n{normality_status}',
                        fontsize=self.config.typography.SIZE_SMALL,
                        fontweight='bold')
            ax.grid(alpha=0.3)

            # Add Shapiro-Wilk p-value if available
            if 'shapiro_wilk' in normality_result:
                p_val = normality_result['shapiro_wilk']['p_value']
                ax.text(0.05, 0.95, f'SW p={p_val:.4f}',
                       transform=ax.transAxes, va='top',
                       fontsize=self.config.typography.SIZE_ANNOTATION,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

        # Hide extra axes
        for idx in range(n_groups, len(axes)):
            axes[idx].axis('off')

        plt.suptitle(f'Q-Q Normality Plots: {metric}',
                    fontsize=self.config.typography.SIZE_TITLE,
                    fontweight='bold')
        plt.tight_layout()

        self.config.save_figure(fig, output_path)
        return fig


class StatisticalCharts:
    """Factory for statistical comparison charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.stat_analyzer = StatisticalAnalyzer()

    def create_pairwise_significance_heatmap(self, data: pd.DataFrame,
                                            group_by: str, metric: str,
                                            output_path: str,
                                            correction_method: str = 'fdr_bh'):
        """Create pairwise significance heatmap with multiple comparison correction.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            metric: Metric to compare
            correction_method: 'bonferroni', 'fdr_bh', etc.
            output_path: Save path
        """
        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        n_groups = len(groups)

        # Compute pairwise p-values
        p_matrix = np.ones((n_groups, n_groups))
        effect_matrix = np.zeros((n_groups, n_groups))

        p_values_flat = []

        for i, group1 in enumerate(groups):
            for j, group2 in enumerate(groups):
                if i >= j:
                    continue

                data1 = data[data[group_by] == group1][metric].dropna().values
                data2 = data[data[group_by] == group2][metric].dropna().values

                if len(data1) > 1 and len(data2) > 1:
                    # Mann-Whitney U test
                    result = self.stat_analyzer.mann_whitney_with_effect_size(data1, data2)
                    p_matrix[i, j] = result['p_value']
                    p_matrix[j, i] = result['p_value']
                    effect_matrix[i, j] = result['rank_biserial_r']
                    effect_matrix[j, i] = -result['rank_biserial_r']  # Reverse sign

                    p_values_flat.append(result['p_value'])

        # Apply multiple comparison correction
        if len(p_values_flat) > 0:
            correction_result = self.stat_analyzer.multiple_comparison_correction(
                p_values_flat, method=correction_method
            )
            p_corrected = correction_result['p_values_corrected']

            # Rebuild matrix with corrected p-values
            p_corrected_matrix = np.ones((n_groups, n_groups))
            idx = 0
            for i in range(n_groups):
                for j in range(i + 1, n_groups):
                    p_corrected_matrix[i, j] = p_corrected[idx]
                    p_corrected_matrix[j, i] = p_corrected[idx]
                    idx += 1
        else:
            p_corrected_matrix = p_matrix

        # Adjust figure size based on number of groups
        fig_width, fig_height = LayoutHelper.adjust_heatmap_size(
            n_groups, n_groups, base_size=0.6, min_size=10, max_size=18
        )
        # Double width for 2 panels
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fig_width * 1.8, fig_height))

        # Determine annotation settings based on matrix size
        show_annot = n_groups <= 10  # Only show numbers if not too dense
        annot_fontsize = max(6, 9 - n_groups // 3)  # Smaller font for larger matrices

        # Truncate long group names
        group_labels = [g[:15] + '...' if len(g) > 15 else g for g in groups]

        # Panel A: P-value heatmap
        # Don't show values and stars together if too crowded
        if show_annot and n_groups <= 6:
            # Show both values and stars
            sns.heatmap(p_corrected_matrix, annot=True, fmt='.3f',
                       cmap='RdYlGn', center=0.05, vmin=0, vmax=0.1,
                       cbar_kws={'label': f'P-value ({correction_method})'},
                       xticklabels=group_labels, yticklabels=group_labels, ax=ax1,
                       linewidths=0.5, linecolor='white',
                       annot_kws={'fontsize': annot_fontsize})

            # Add significance stars (smaller if many groups)
            star_fontsize = max(6, self.config.typography.SIZE_ANNOTATION - n_groups // 4)
            for i in range(n_groups):
                for j in range(n_groups):
                    p_val = p_corrected_matrix[i, j]
                    if p_val < 0.0001:
                        stars = '****'
                    elif p_val < 0.001:
                        stars = '***'
                    elif p_val < 0.01:
                        stars = '**'
                    elif p_val < 0.05:
                        stars = '*'
                    else:
                        stars = ''

                    if stars:
                        ax1.text(j + 0.5, i + 0.75, stars, ha='center', va='center',
                                color='white', fontweight='bold',
                                fontsize=star_fontsize)
        else:
            # Just show stars for crowded matrices
            star_matrix = np.empty((n_groups, n_groups), dtype=object)
            for i in range(n_groups):
                for j in range(n_groups):
                    p_val = p_corrected_matrix[i, j]
                    if i == j:
                        star_matrix[i, j] = '─'
                    elif p_val < 0.0001:
                        star_matrix[i, j] = '****'
                    elif p_val < 0.001:
                        star_matrix[i, j] = '***'
                    elif p_val < 0.01:
                        star_matrix[i, j] = '**'
                    elif p_val < 0.05:
                        star_matrix[i, j] = '*'
                    else:
                        star_matrix[i, j] = 'ns'

            sns.heatmap(p_corrected_matrix, annot=star_matrix, fmt='',
                       cmap='RdYlGn', center=0.05, vmin=0, vmax=0.1,
                       cbar_kws={'label': f'P-value ({correction_method})'},
                       xticklabels=group_labels, yticklabels=group_labels, ax=ax1,
                       linewidths=0.5, linecolor='white',
                       annot_kws={'fontsize': annot_fontsize})

        ax1.set_title('(A) Pairwise Statistical Significance', fontweight='bold', pad=10)

        # Rotate labels if needed
        if n_groups > 4 or max(len(g) for g in groups) > 10:
            LayoutHelper.rotate_xlabels(ax1, rotation=45, ha='right')
            LayoutHelper.rotate_ylabels(ax1, rotation=0, ha='right')

        # Panel B: Effect size heatmap
        sns.heatmap(effect_matrix, annot=show_annot, fmt='.2f',
                   cmap='RdBu_r', center=0, vmin=-1, vmax=1,
                   cbar_kws={'label': 'Rank-Biserial r'},
                   xticklabels=group_labels, yticklabels=group_labels, ax=ax2,
                   linewidths=0.5, linecolor='white',
                   annot_kws={'fontsize': annot_fontsize})

        ax2.set_title('(B) Effect Size (Rank-Biserial)', fontweight='bold', pad=10)

        # Rotate labels if needed
        if n_groups > 4 or max(len(g) for g in groups) > 10:
            LayoutHelper.rotate_xlabels(ax2, rotation=45, ha='right')
            LayoutHelper.rotate_ylabels(ax2, rotation=0, ha='right')

        plt.suptitle(f'Pairwise Comparison: {metric}\n(Corrected: {correction_method})',
                    fontsize=self.config.typography.SIZE_TITLE,
                    fontweight='bold', y=1.02)

        LayoutHelper.apply_tight_layout(fig, pad=2.5)
        self.config.save_figure(fig, output_path)
        return fig


class DistributionCharts:
    """Factory for distribution visualization charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config

    def create_advanced_distribution(self, data: pd.DataFrame,
                                    group_by: str, metric: str,
                                    output_path: str):
        """Create comprehensive distribution visualization.

        Combines violin, box, strip, and KDE plots.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            metric: Metric to visualize
            output_path: Save path
        """
        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        n_groups = len(groups)

        # Adjust figure size based on number of groups
        base_width = max(12, n_groups * 1.2)
        base_height = max(10, 8 + n_groups * 0.15)
        fig = plt.figure(figsize=(base_width, base_height))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.35)

        colors = self.config.get_colors(n_groups)

        # Panel A: Violin + Box + Strip
        ax1 = fig.add_subplot(gs[0, :])

        parts = ax1.violinplot(
            [data[data[group_by] == g][metric].dropna().values for g in groups],
            positions=range(len(groups)),
            showmeans=True,
            showmedians=True,
            widths=0.7
        )

        # Color violins
        for pc, color in zip(parts['bodies'], colors):
            pc.set_facecolor(color)
            pc.set_alpha(0.6)

        # Add strip plot
        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group][metric].dropna().values
            x_pos = np.random.normal(idx, 0.04, size=len(group_data))
            ax1.scatter(x_pos, group_data, alpha=0.3, s=20,
                       color=colors[idx], edgecolors='black', linewidths=0.3)

        ax1.set_xticks(range(len(groups)))
        # Truncate and rotate labels based on group count
        group_labels = [g[:20] + '...' if len(g) > 20 else g for g in groups]
        rotation = 45 if n_groups > 3 or max(len(g) for g in groups) > 12 else 0
        ax1.set_xticklabels(group_labels, rotation=rotation,
                           ha='right' if rotation > 0 else 'center',
                           fontsize=self.config.typography.SIZE_AXIS_TICK)
        ax1.set_ylabel(metric.replace('_', ' ').title(), fontweight='bold')
        ax1.set_title('(A) Distribution with Individual Points', fontweight='bold', pad=10)
        ax1.grid(axis='y', alpha=0.3)

        # Panel B: KDE
        ax2 = fig.add_subplot(gs[1, 0])
        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group][metric].dropna().values
            if len(group_data) > 2:
                from scipy.stats import gaussian_kde
                kde = gaussian_kde(group_data)
                x_range = np.linspace(group_data.min(), group_data.max(), 200)
                # Truncate label for legend
                label = group[:15] + '...' if len(group) > 15 else group
                ax2.plot(x_range, kde(x_range), label=label, color=colors[idx],
                        linewidth=2, alpha=0.8)

        ax2.set_xlabel(metric.replace('_', ' ').title(), fontweight='bold')
        ax2.set_ylabel('Density', fontweight='bold')
        ax2.set_title('(B) Kernel Density Estimation', fontweight='bold', pad=10)
        # Smart legend placement
        LayoutHelper.improve_legend_placement(ax2,
                                             ncol=min(2, (n_groups + 2) // 3),
                                             loc='best',
                                             fontsize=self.config.typography.SIZE_LEGEND)
        ax2.grid(alpha=0.3)

        # Panel C: ECDF
        ax3 = fig.add_subplot(gs[1, 1])
        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group][metric].dropna().values
            if len(group_data) > 0:
                sorted_data = np.sort(group_data)
                y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
                # Truncate label for legend
                label = group[:15] + '...' if len(group) > 15 else group
                ax3.plot(sorted_data, y, label=label, color=colors[idx],
                        linewidth=2, alpha=0.8, marker='o', markersize=3,
                        markevery=max(1, len(sorted_data) // 20))

        ax3.set_xlabel(metric.replace('_', ' ').title(), fontweight='bold')
        ax3.set_ylabel('Cumulative Probability', fontweight='bold')
        ax3.set_title('(C) Empirical CDF', fontweight='bold', pad=10)
        # Smart legend placement
        LayoutHelper.improve_legend_placement(ax3,
                                             ncol=min(2, (n_groups + 2) // 3),
                                             loc='best',
                                             fontsize=self.config.typography.SIZE_LEGEND)
        ax3.grid(alpha=0.3)

        plt.suptitle(f'Distribution Analysis: {metric}',
                    fontsize=self.config.typography.SIZE_TITLE + 1,
                    fontweight='bold', y=0.995)

        LayoutHelper.apply_tight_layout(fig, pad=2.0)
        self.config.save_figure(fig, output_path)
        return fig


class ResourceCharts:
    """Factory for resource utilization charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config

    def create_resource_efficiency_analysis(self, data: pd.DataFrame,
                                           group_by: str, output_path: str):
        """Create comprehensive resource efficiency analysis.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            output_path: Save path
        """
        fig = plt.figure(figsize=self.config.get_figure_size('double_square'))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        colors = self.config.get_colors(len(groups), groups)

        # Panel A: Memory efficiency (Memory / Time)
        ax1 = fig.add_subplot(gs[0, 0])
        mem_eff = data.groupby(group_by).agg({
            'peak_memory_mb': 'mean',
            'wall_clock_time_sec': 'mean'
        })
        mem_eff['efficiency'] = mem_eff['peak_memory_mb'] / mem_eff['wall_clock_time_sec']
        mem_eff = mem_eff.sort_values('efficiency')

        x_pos = np.arange(len(mem_eff))
        ax1.barh(x_pos, mem_eff['efficiency'], color=colors, edgecolor='black', linewidth=0.8)
        ax1.set_yticks(x_pos)
        ax1.set_yticklabels(mem_eff.index)
        ax1.set_xlabel('Memory Efficiency (KB/sec)', fontweight='bold')
        ax1.set_title('(A) Memory per Second', fontweight='bold', pad=10)
        ax1.grid(axis='x', alpha=0.3)

        # Panel B: CPU efficiency
        ax2 = fig.add_subplot(gs[0, 1])
        cpu_eff = data.groupby(group_by)['cpu_efficiency'].mean().sort_values()
        cpu_eff_pct = cpu_eff * 100

        x_pos = np.arange(len(cpu_eff_pct))
        bars = ax2.barh(x_pos, cpu_eff_pct, color=colors, edgecolor='black', linewidth=0.8)
        ax2.axvline(100, color='red', linestyle='--', linewidth=1.5, label='100% (CPU-bound)')
        ax2.set_yticks(x_pos)
        ax2.set_yticklabels(cpu_eff_pct.index)
        ax2.set_xlabel('CPU Efficiency (%)', fontweight='bold')
        ax2.set_title('(B) CPU Utilization', fontweight='bold', pad=10)
        ax2.legend(fontsize=self.config.typography.SIZE_LEGEND)
        ax2.grid(axis='x', alpha=0.3)

        # Panel C: I/O wait
        ax3 = fig.add_subplot(gs[1, 0])
        io_wait = data.groupby(group_by)['io_wait_percent'].mean().sort_values()

        x_pos = np.arange(len(io_wait))
        bars = ax3.barh(x_pos, io_wait, color=colors, edgecolor='black', linewidth=0.8)
        ax3.axvline(50, color='red', linestyle='--', linewidth=1.5, label='50% threshold')
        ax3.set_yticks(x_pos)
        ax3.set_yticklabels(io_wait.index)
        ax3.set_xlabel('I/O Wait (%)', fontweight='bold')
        ax3.set_title('(C) I/O Blocking Time', fontweight='bold', pad=10)
        ax3.legend(fontsize=self.config.typography.SIZE_LEGEND)
        ax3.grid(axis='x', alpha=0.3)

        # Panel D: Throughput normalized by memory
        ax4 = fig.add_subplot(gs[1, 1])
        throughput_mem = data.groupby(group_by).agg({
            'throughput_kb_per_sec': 'mean',
            'peak_memory_mb': 'mean'
        })
        throughput_mem['norm_throughput'] = (
            throughput_mem['throughput_kb_per_sec'] / throughput_mem['peak_memory_mb'] * 1000
        )
        throughput_mem = throughput_mem.sort_values('norm_throughput', ascending=False)

        x_pos = np.arange(len(throughput_mem))
        ax4.barh(x_pos, throughput_mem['norm_throughput'], color=colors,
                edgecolor='black', linewidth=0.8)
        ax4.set_yticks(x_pos)
        ax4.set_yticklabels(throughput_mem.index)
        ax4.set_xlabel('Throughput per GB Memory', fontweight='bold')
        ax4.set_title('(D) Memory-Normalized Throughput', fontweight='bold', pad=10)
        ax4.grid(axis='x', alpha=0.3)

        plt.suptitle('Resource Efficiency Analysis',
                    fontsize=self.config.typography.SIZE_TITLE + 1,
                    fontweight='bold', y=0.995)

        self.config.save_figure(fig, output_path)
        return fig


class ScalabilityCharts:
    """Factory for scalability and complexity analysis charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.reg_analyzer = RegressionAnalyzer()

    def create_speedup_comparison(self, data: pd.DataFrame, baseline_strategy: str,
                                  output_path: str):
        """Create speedup comparison chart (log scale time + throughput).

        This is a publication-standard visualization showing:
        - Panel A: Time vs Size (log scale) with speedup annotations
        - Panel B: Throughput vs Size (scalability indicator)

        Args:
            data: Benchmark DataFrame
            baseline_strategy: Reference strategy for speedup calculation
            output_path: Save path
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.config.get_figure_size('double_wide'))

        # Sort by version for consistent grouping
        strategies = self.config.sort_strategies_by_version([
            s for s in data['version_strategy'].unique() if s != baseline_strategy
        ])
        all_strategies = self.config.sort_strategies_by_version([baseline_strategy] + strategies)
        # Use consistent colors for version+strategy
        colors = self.config.get_colors(len(all_strategies), all_strategies)

        # Prepare data: group by strategy and file size
        size_col = 'file_size_mb'
        time_col = 'wall_clock_time_sec'
        throughput_col = 'throughput_kb_per_sec'

        # Panel A: Time vs Size (LOG SCALE)
        for idx, strategy in enumerate(all_strategies):
            strategy_data = data[data['version_strategy'] == strategy]

            # Aggregate by file size (mean)
            size_time = strategy_data.groupby(size_col).agg({
                time_col: 'mean'
            }).reset_index()

            # Sort by size
            size_time = size_time.sort_values(size_col)

            # Plot with markers
            markers = ['o', 's', '^', 'D', 'v', '<', '>']
            marker = markers[idx % len(markers)]
            linestyle = '--' if strategy == baseline_strategy else '-'
            linewidth = 2.0 if strategy == baseline_strategy else 2.5

            ax1.plot(size_time[size_col], size_time[time_col],
                    marker=marker, linestyle=linestyle,
                    color=colors[idx], label=strategy,
                    linewidth=linewidth, markersize=8, alpha=0.9)

        ax1.set_yscale('log')
        ax1.set_xscale('log')
        ax1.set_title('(A) Processing Time vs File Size', fontweight='bold', pad=10)
        ax1.set_xlabel('File Size (MB)', fontweight='bold')
        ax1.set_ylabel('Time (seconds, log scale)', fontweight='bold')
        ax1.legend(fontsize=self.config.typography.SIZE_LEGEND, loc='best')
        ax1.grid(True, which='both', alpha=0.3, linestyle=':')

        # Add speedup annotations at median file size
        baseline_data = data[data['version_strategy'] == baseline_strategy]
        median_size = data[size_col].median()

        # Find baseline time at median size
        baseline_at_median = baseline_data[
            (baseline_data[size_col] >= median_size * 0.9) &
            (baseline_data[size_col] <= median_size * 1.1)
        ][time_col].mean()

        if not np.isnan(baseline_at_median):
            for idx, strategy in enumerate(strategies):
                strategy_data = data[data['version_strategy'] == strategy]
                strategy_at_median = strategy_data[
                    (strategy_data[size_col] >= median_size * 0.9) &
                    (strategy_data[size_col] <= median_size * 1.1)
                ][time_col].mean()

                if not np.isnan(strategy_at_median) and strategy_at_median > 0:
                    speedup = baseline_at_median / strategy_at_median

                    # Only annotate significant speedups
                    if speedup > 1.5 or speedup < 0.67:
                        ax1.annotate(f'{speedup:.1f}×',
                                    xy=(median_size, strategy_at_median),
                                    xytext=(10, -10 * idx),
                                    textcoords='offset points',
                                    fontsize=self.config.typography.SIZE_ANNOTATION,
                                    fontweight='bold',
                                    color=colors[idx + 1],
                                    bbox=dict(boxstyle='round,pad=0.3',
                                             facecolor='white',
                                             edgecolor=colors[idx + 1],
                                             alpha=0.9))

        # Panel B: Throughput vs Size
        for idx, strategy in enumerate(all_strategies):
            strategy_data = data[data['version_strategy'] == strategy]

            # Aggregate by file size
            size_throughput = strategy_data.groupby(size_col).agg({
                throughput_col: 'mean'
            }).reset_index()

            # Sort by size
            size_throughput = size_throughput.sort_values(size_col)

            # Plot
            markers = ['o', 's', '^', 'D', 'v', '<', '>']
            marker = markers[idx % len(markers)]
            linestyle = '--' if strategy == baseline_strategy else '-'
            linewidth = 2.0 if strategy == baseline_strategy else 2.5

            ax2.plot(size_throughput[size_col], size_throughput[throughput_col],
                    marker=marker, linestyle=linestyle,
                    color=colors[idx], label=strategy,
                    linewidth=linewidth, markersize=8, alpha=0.9)

        ax2.set_xscale('log')
        ax2.set_title('(B) Throughput & Scalability', fontweight='bold', pad=10)
        ax2.set_xlabel('File Size (MB)', fontweight='bold')
        ax2.set_ylabel('Throughput (KB/sec)', fontweight='bold')
        ax2.legend(fontsize=self.config.typography.SIZE_LEGEND, loc='best')
        ax2.grid(True, alpha=0.3, linestyle=':')

        # Add annotation for scalability
        # Throughput should be constant for O(n) algorithms
        for idx, strategy in enumerate(all_strategies):
            strategy_data = data[data['version_strategy'] == strategy]
            throughputs = strategy_data.groupby(size_col)[throughput_col].mean()

            if len(throughputs) > 1:
                # Coefficient of variation (lower = more stable = better scalability)
                cv = throughputs.std() / throughputs.mean()

                if cv < 0.2:  # Stable throughput
                    max_size = throughputs.index.max()
                    max_throughput = throughputs.loc[max_size]

                    ax2.text(max_size * 1.1, max_throughput,
                            f'Stable\n(CV={cv:.2f})',
                            fontsize=self.config.typography.SIZE_ANNOTATION - 1,
                            color=colors[idx],
                            bbox=dict(boxstyle='round,pad=0.2',
                                     facecolor='white',
                                     edgecolor=colors[idx],
                                     alpha=0.8))

        plt.suptitle(f'Speedup Analysis (Baseline: {baseline_strategy})',
                    fontsize=self.config.typography.SIZE_TITLE + 1,
                    fontweight='bold', y=0.98)

        plt.tight_layout()
        self.config.save_figure(fig, output_path)
        return fig

    def create_scaling_analysis(self, data: pd.DataFrame, group_by: str, output_path: str):
        """Create comprehensive scaling analysis with log-log plots.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            output_path: Save path
        """
        from .statistics import RegressionAnalyzer

        fig = plt.figure(figsize=self.config.get_figure_size('double_square'))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        colors = self.config.get_colors(len(groups), groups)

        # Panel A: Linear scale (time vs size)
        ax1 = fig.add_subplot(gs[0, 0])
        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group]
            valid = (group_data['file_size_mb'] > 0) & (group_data['wall_clock_time_sec'] > 0)
            x = group_data.loc[valid, 'file_size_mb'].values
            y = group_data.loc[valid, 'wall_clock_time_sec'].values

            ax1.scatter(x, y, alpha=0.5, s=30, color=colors[idx], label=group,
                       edgecolors='black', linewidth=0.3)

        ax1.set_xlabel('File Size (MB)', fontweight='bold')
        ax1.set_ylabel('Execution Time (sec)', fontweight='bold')
        ax1.set_title('(A) Linear Scale', fontweight='bold', pad=10)
        ax1.legend(fontsize=self.config.typography.SIZE_LEGEND - 1, loc='best')
        ax1.grid(alpha=0.3)

        # Panel B: Log-log scale (identify complexity)
        ax2 = fig.add_subplot(gs[0, 1])
        complexity_results = []

        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group]
            valid = (group_data['file_size_mb'] > 0) & (group_data['wall_clock_time_sec'] > 0)
            x = group_data.loc[valid, 'file_size_mb'].values
            y = group_data.loc[valid, 'wall_clock_time_sec'].values

            if len(x) < 3:
                continue

            # Log-log regression
            result = RegressionAnalyzer.log_log_regression(x, y)

            if 'error' not in result:
                ax2.scatter(x, y, alpha=0.5, s=30, color=colors[idx], label=group,
                           edgecolors='black', linewidth=0.3)

                # Plot fitted line in log space
                x_sorted = np.sort(x)
                log_x_sorted = np.log(x_sorted)
                log_y_fit = result['intercept'] + result['slope'] * log_x_sorted
                y_fit = np.exp(log_y_fit)
                ax2.plot(x_sorted, y_fit, '--', color=colors[idx], linewidth=2, alpha=0.8)

                complexity_results.append({
                    'group': group,
                    'slope': result['slope'],
                    'complexity': result['complexity'],
                    'r_squared': result['r_squared']
                })

        ax2.set_xlabel('File Size (MB)', fontweight='bold')
        ax2.set_ylabel('Execution Time (sec)', fontweight='bold')
        ax2.set_title('(B) Log-Log Scale (Complexity)', fontweight='bold', pad=10)
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        ax2.legend(fontsize=self.config.typography.SIZE_LEGEND - 1, loc='best')
        ax2.grid(alpha=0.3, which='both')

        # Panel C: Complexity comparison (slopes from log-log)
        if complexity_results:
            ax3 = fig.add_subplot(gs[1, 0])
            groups_with_results = [r['group'] for r in complexity_results]
            slopes = [r['slope'] for r in complexity_results]

            x_pos = np.arange(len(slopes))
            bars = ax3.barh(x_pos, slopes, color=colors[:len(slopes)],
                           edgecolor='black', linewidth=0.8)

            # Reference lines
            ax3.axvline(1.0, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='O(n)')
            ax3.axvline(1.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='O(n^1.5)')
            ax3.axvline(2.0, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='O(n²)')

            ax3.set_yticks(x_pos)
            ax3.set_yticklabels(groups_with_results)
            ax3.set_xlabel('Scaling Exponent (log-log slope)', fontweight='bold')
            ax3.set_title('(C) Algorithmic Complexity', fontweight='bold', pad=10)
            ax3.legend(fontsize=self.config.typography.SIZE_LEGEND)
            ax3.grid(axis='x', alpha=0.3)

            # Add complexity labels
            for i, result in enumerate(complexity_results):
                ax3.text(result['slope'] + 0.05, i, f"{result['complexity']} (R²={result['r_squared']:.2f})",
                        va='center', fontsize=self.config.typography.SIZE_ANNOTATION)

        # Panel D: Throughput vs size (should be constant for linear algorithms)
        ax4 = fig.add_subplot(gs[1, 1])
        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group]
            valid = (group_data['file_size_mb'] > 0) & (group_data['throughput_kb_per_sec'] > 0)
            x = group_data.loc[valid, 'file_size_mb'].values
            y = group_data.loc[valid, 'throughput_kb_per_sec'].values

            if len(x) > 0:
                ax4.scatter(x, y, alpha=0.5, s=30, color=colors[idx], label=group,
                           edgecolors='black', linewidth=0.3)

                # Add mean line
                mean_throughput = np.mean(y)
                ax4.axhline(mean_throughput, color=colors[idx], linestyle='--',
                           linewidth=1.5, alpha=0.5)

        ax4.set_xlabel('File Size (MB)', fontweight='bold')
        ax4.set_ylabel('Throughput (KB/sec)', fontweight='bold')
        ax4.set_title('(D) Throughput Stability', fontweight='bold', pad=10)
        ax4.legend(fontsize=self.config.typography.SIZE_LEGEND - 1, loc='best')
        ax4.grid(alpha=0.3)

        plt.suptitle('Scalability and Complexity Analysis',
                    fontsize=self.config.typography.SIZE_TITLE + 1,
                    fontweight='bold', y=0.995)

        self.config.save_figure(fig, output_path)
        return fig

    def create_scaling_analysis_simplified(self, data: pd.DataFrame, group_by: str, output_path: str):
        """Create simplified scaling analysis with 3 panels (A, B, C) side by side.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            output_path: Save path
        """
        from .statistics import RegressionAnalyzer

        fig = plt.figure(figsize=(self.config.get_figure_size('double_square')[0] * 1.5, 
                                   self.config.get_figure_size('double_square')[1] * 0.5))
        gs = gridspec.GridSpec(1, 3, figure=fig, hspace=0.3, wspace=0.3)

        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        colors = self.config.get_colors(len(groups), groups)

        # Panel A: Linear scale (time vs size)
        ax1 = fig.add_subplot(gs[0, 0])
        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group]
            valid = (group_data['file_size_mb'] > 0) & (group_data['wall_clock_time_sec'] > 0)
            x = group_data.loc[valid, 'file_size_mb'].values
            y = group_data.loc[valid, 'wall_clock_time_sec'].values

            ax1.scatter(x, y, alpha=0.5, s=30, color=colors[idx], label=group,
                       edgecolors='black', linewidth=0.3)

        ax1.set_xlabel('File Size (MB)', fontweight='bold')
        ax1.set_ylabel('Execution Time (sec)', fontweight='bold')
        ax1.set_title('(A) Linear Scale', fontweight='bold', pad=10)
        ax1.legend(fontsize=self.config.typography.SIZE_LEGEND - 1, loc='best')
        ax1.grid(alpha=0.3)

        # Panel B: Log-log scale (identify complexity)
        ax2 = fig.add_subplot(gs[0, 1])
        complexity_results = []

        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group]
            valid = (group_data['file_size_mb'] > 0) & (group_data['wall_clock_time_sec'] > 0)
            x = group_data.loc[valid, 'file_size_mb'].values
            y = group_data.loc[valid, 'wall_clock_time_sec'].values

            if len(x) < 3:
                continue

            # Log-log regression
            result = RegressionAnalyzer.log_log_regression(x, y)

            if 'error' not in result:
                ax2.scatter(x, y, alpha=0.5, s=30, color=colors[idx], label=group,
                           edgecolors='black', linewidth=0.3)

                # Plot fitted line in log space
                x_sorted = np.sort(x)
                log_x_sorted = np.log(x_sorted)
                log_y_fit = result['intercept'] + result['slope'] * log_x_sorted
                y_fit = np.exp(log_y_fit)
                ax2.plot(x_sorted, y_fit, '--', color=colors[idx], linewidth=2, alpha=0.8)

                complexity_results.append({
                    'group': group,
                    'slope': result['slope'],
                    'complexity': result['complexity'],
                    'r_squared': result['r_squared']
                })

        ax2.set_xlabel('File Size (MB)', fontweight='bold')
        ax2.set_ylabel('Execution Time (sec)', fontweight='bold')
        ax2.set_title('(B) Log-Log Scale (Complexity)', fontweight='bold', pad=10)
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        ax2.legend(fontsize=self.config.typography.SIZE_LEGEND - 1, loc='best')
        ax2.grid(alpha=0.3, which='both')

        # Panel C: Throughput vs size (should be constant for linear algorithms)
        ax3 = fig.add_subplot(gs[0, 2])
        for idx, group in enumerate(groups):
            group_data = data[data[group_by] == group]
            valid = (group_data['file_size_mb'] > 0) & (group_data['throughput_kb_per_sec'] > 0)
            x = group_data.loc[valid, 'file_size_mb'].values
            y = group_data.loc[valid, 'throughput_kb_per_sec'].values

            if len(x) > 0:
                ax3.scatter(x, y, alpha=0.5, s=30, color=colors[idx], label=group,
                           edgecolors='black', linewidth=0.3)

                # Add mean line
                mean_throughput = np.mean(y)
                ax3.axhline(mean_throughput, color=colors[idx], linestyle='--',
                           linewidth=1.5, alpha=0.5)

        ax3.set_xlabel('File Size (MB)', fontweight='bold')
        ax3.set_ylabel('Throughput (KB/sec)', fontweight='bold')
        ax3.set_title('(C) Throughput Stability', fontweight='bold', pad=10)
        ax3.legend(fontsize=self.config.typography.SIZE_LEGEND - 1, loc='best')
        ax3.grid(alpha=0.3)

        plt.suptitle('Scalability Analysis',
                    fontsize=self.config.typography.SIZE_TITLE + 1,
                    fontweight='bold', y=0.98)

        self.config.save_figure(fig, output_path)
        return fig

    def create_polynomial_comparison(self, data: pd.DataFrame, group_by: str, output_path: str):
        """Compare linear vs polynomial models.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            output_path: Save path
        """
        fig = plt.figure(figsize=self.config.get_figure_size('double_wide'))
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)

        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))[:6]  # Max 6 groups
        colors = self.config.get_colors(len(groups), groups)

        for idx, group in enumerate(groups):
            row = idx // 3
            col = idx % 3
            ax = fig.add_subplot(gs[row, col])

            group_data = data[data[group_by] == group]
            valid = (group_data['file_size_kb'] > 0) & (group_data['wall_clock_time_sec'] > 0)
            x = group_data.loc[valid, 'file_size_kb'].values
            y = group_data.loc[valid, 'wall_clock_time_sec'].values

            if len(x) < 3:
                ax.text(0.5, 0.5, f'{group}\nInsufficient data',
                       ha='center', va='center', transform=ax.transAxes)
                continue

            # Scatter
            ax.scatter(x, y, alpha=0.5, s=20, color=colors[idx],
                      edgecolors='black', linewidth=0.3)

            # Linear fit
            linear_result = self.reg_analyzer.linear_regression(x, y)
            x_sorted = np.sort(x)
            y_linear = linear_result.intercept + linear_result.slope * x_sorted
            ax.plot(x_sorted, y_linear, '--', color='blue', linewidth=2, alpha=0.7,
                   label=f'Linear (R²={linear_result.r_squared:.3f})')

            # Quadratic fit
            poly_result = self.reg_analyzer.polynomial_regression(x, y, degree=2)
            y_poly = poly_result['polynomial'](x_sorted)
            ax.plot(x_sorted, y_poly, '-', color='red', linewidth=2, alpha=0.7,
                   label=f'Quadratic (R²={poly_result["r_squared"]:.3f})')

            ax.set_xlabel('File Size (KB)', fontweight='bold',
                         fontsize=self.config.typography.SIZE_SMALL)
            ax.set_ylabel('Time (sec)', fontweight='bold',
                         fontsize=self.config.typography.SIZE_SMALL)
            ax.set_title(f'{group}', fontweight='bold', pad=5,
                        fontsize=self.config.typography.SIZE_SMALL)
            ax.legend(fontsize=self.config.typography.SIZE_ANNOTATION)
            ax.grid(alpha=0.3)

            # Add improvement annotation
            if poly_result['better_than_linear']:
                improvement = poly_result['improvement'] * 100
                ax.text(0.98, 0.02, f'↑{improvement:.1f}% better',
                       transform=ax.transAxes, ha='right', va='bottom',
                       fontsize=self.config.typography.SIZE_ANNOTATION,
                       bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

        plt.suptitle('Linear vs Polynomial Model Comparison',
                    fontsize=self.config.typography.SIZE_TITLE,
                    fontweight='bold', y=0.995)

        self.config.save_figure(fig, output_path)
        return fig


class CorrelationCharts:
    """Factory for correlation and association charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config

    def create_correlation_heatmap(self, data: pd.DataFrame, output_path: str,
                                  method: str = 'spearman'):
        """Create correlation heatmap with significance indicators.

        Args:
            data: Benchmark DataFrame
            method: 'pearson', 'spearman', or 'kendall'
            output_path: Save path
        """
        from .statistics import CorrelationAnalyzer

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.config.get_figure_size('double_wide'))

        # Select numeric metrics
        metric_cols = [
            'wall_clock_time_sec', 'user_time_sec', 'system_time_sec',
            'peak_memory_mb', 'cpu_percent', 'io_wait_percent',
            'throughput_kb_per_sec', 'file_size_mb'
        ]
        available_cols = [c for c in metric_cols if c in data.columns]
        data_numeric = data[available_cols].dropna()

        # Compute correlation
        analyzer = CorrelationAnalyzer()
        result = analyzer.correlation_matrix(data_numeric, method=method)

        corr_matrix = result['correlation_matrix']
        p_matrix = result['p_value_matrix']

        # Panel A: Correlation heatmap
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='RdBu_r',
                   center=0, vmin=-1, vmax=1,
                   cbar_kws={'label': f'{method.capitalize()} Correlation'},
                   ax=ax1, linewidths=0.5, linecolor='white',
                   square=True)
        ax1.set_title('(A) Correlation Matrix', fontweight='bold', pad=10)

        # Add significance stars
        for i in range(len(corr_matrix)):
            for j in range(len(corr_matrix)):
                p_val = p_matrix.iloc[i, j]
                if p_val < 0.001:
                    stars = '***'
                elif p_val < 0.01:
                    stars = '**'
                elif p_val < 0.05:
                    stars = '*'
                else:
                    stars = ''

                if stars and i != j:
                    ax1.text(j + 0.5, i + 0.8, stars, ha='center', va='center',
                            color='white', fontweight='bold',
                            fontsize=self.config.typography.SIZE_ANNOTATION)

        # Panel B: P-value heatmap
        # Use -log10(p) for better visualization
        log_p = -np.log10(p_matrix + 1e-10)  # Add small constant to avoid log(0)
        sns.heatmap(log_p, annot=False, cmap='YlOrRd',
                   cbar_kws={'label': '-log10(p-value)'},
                   ax=ax2, linewidths=0.5, linecolor='white',
                   square=True)
        ax2.set_title('(B) Significance (-log10 p)', fontweight='bold', pad=10)

        # Add reference lines
        ax2.axhline(-np.log10(0.05) * len(corr_matrix), color='blue',
                   linestyle='--', linewidth=2, label='p=0.05')
        ax2.axhline(-np.log10(0.01) * len(corr_matrix), color='red',
                   linestyle='--', linewidth=2, label='p=0.01')

        plt.suptitle(f'Correlation Analysis ({method.capitalize()})',
                    fontsize=self.config.typography.SIZE_TITLE,
                    fontweight='bold', y=0.995)
        plt.tight_layout()

        self.config.save_figure(fig, output_path)
        return fig


class VarianceCharts:
    """Factory for variance analysis (ANOVA) charts."""

    def __init__(self, config: VisualizationConfig):
        self.config = config

    def create_anova_summary(self, data: pd.DataFrame, group_by: str,
                            output_path: str, metric: str = 'wall_clock_time_sec'):
        """Create ANOVA/Kruskal-Wallis analysis visualization.

        Args:
            data: Benchmark DataFrame
            group_by: Grouping column
            metric: Metric to analyze
            output_path: Save path
        """
        from .statistics import VarianceAnalyzer

        fig = plt.figure(figsize=self.config.get_figure_size('double_wide'))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        groups = self.config.sort_strategies_by_version(list(data[group_by].unique()))
        colors = self.config.get_colors(len(groups), groups)

        # Prepare data
        group_arrays = [data[data[group_by] == g][metric].dropna().values for g in groups]

        # Run both tests
        analyzer = VarianceAnalyzer()
        anova_result = analyzer.one_way_anova(group_arrays)
        kw_result = analyzer.kruskal_wallis(group_arrays)
        levene_result = analyzer.levene_test(group_arrays)

        # Panel A: Box plot with means
        ax1 = fig.add_subplot(gs[0, :])
        bp = ax1.boxplot(group_arrays, labels=groups, patch_artist=True,
                         notch=True, showmeans=True,
                         meanprops=dict(marker='D', markerfacecolor='red', markersize=6))

        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax1.set_ylabel(metric.replace('_', ' ').title(), fontweight='bold')
        ax1.set_title('(A) Group Comparison with Means', fontweight='bold', pad=10)
        ax1.grid(axis='y', alpha=0.3)

        # Rotate labels if needed
        if len(groups) > 5:
            ax1.set_xticklabels(groups, rotation=45, ha='right')

        # Panel B: ANOVA results
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.axis('off')

        anova_text = [
            "PARAMETRIC TEST (ANOVA)",
            "─" * 40,
            f"F-statistic: {anova_result['f_statistic']:.4f}",
            f"p-value: {anova_result['p_value']:.4e}",
            f"η² (eta-squared): {anova_result['eta_squared']:.4f}",
            f"Effect: {anova_result['effect_interpretation']}",
            "",
            "ASSUMPTIONS:",
            f"• Homoscedasticity: {levene_result['interpretation']}",
            f"  (Levene p={levene_result['p_value']:.4f})",
        ]

        ax2.text(0.1, 0.9, '\n'.join(anova_text), transform=ax2.transAxes,
                va='top', fontsize=self.config.typography.SIZE_SMALL,
                fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

        # Panel C: Kruskal-Wallis results
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.axis('off')

        kw_text = [
            "NON-PARAMETRIC TEST (Kruskal-Wallis)",
            "─" * 40,
            f"H-statistic: {kw_result['h_statistic']:.4f}",
            f"p-value: {kw_result['p_value']:.4e}",
            f"ε² (epsilon-squared): {kw_result['epsilon_squared']:.4f}",
            "",
            "CONCLUSION:",
            "✓ Use this if normality violated",
            "✓ Distribution-free test",
            f"✓ Detects differences in medians",
        ]

        ax3.text(0.1, 0.9, '\n'.join(kw_text), transform=ax3.transAxes,
                va='top', fontsize=self.config.typography.SIZE_SMALL,
                fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

        plt.suptitle(f'Analysis of Variance: {metric}',
                    fontsize=self.config.typography.SIZE_TITLE,
                    fontweight='bold', y=0.995)

        self.config.save_figure(fig, output_path)
        return fig


class ChartFactory:
    """Main factory for creating all chart types.

    Usage:
        factory = ChartFactory(config)
        factory.performance.create_normalized_performance_comparison(data, output_path)
    """

    def __init__(self, config: VisualizationConfig):
        """Initialize factory with configuration.

        Args:
            config: VisualizationConfig instance
        """
        self.config = config
        self.performance = PerformanceCharts(config)
        self.regression = RegressionCharts(config)
        self.statistical = StatisticalCharts(config)
        self.distribution = DistributionCharts(config)
        self.resource = ResourceCharts(config)
        self.scalability = ScalabilityCharts(config)
        self.correlation = CorrelationCharts(config)
        self.variance = VarianceCharts(config)
