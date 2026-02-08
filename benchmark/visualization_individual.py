#!/usr/bin/env python3
"""
Individual Visualization Generator for Benchmark Analysis
Creates separate, clean plots for each metric with proper spacing
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path


class IndividualVisualizer:
    """Generate individual, clean visualizations."""
    
    def __init__(self, analyzer, output_dir):
        self.analyzer = analyzer
        self.df = analyzer.df_success
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean style
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams.update({
            'figure.dpi': 150,
            'savefig.dpi': 300,
            'font.size': 11,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'figure.autolayout': True
        })
    
    def generate_all(self):
        """Generate all individual plots."""
        count = 0
        
        count += self.plot_execution_time()
        count += self.plot_throughput()
        count += self.plot_memory_usage()
        count += self.plot_cpu_efficiency()
        count += self.plot_io_wait()
        count += self.plot_time_distribution()
        count += self.plot_performance_matrix()
        count += self.plot_efficiency_scatter()
        
        # Separate resource plots (previously combined in plot 8)
        count += self.plot_context_switches()
        count += self.plot_file_io()
        count += self.plot_memory_efficiency()
        count += self.plot_throughput_vs_size()
        
        self.create_markdown_report()
        
        return count
    
    def plot_execution_time(self):
        """Plot 1: Execution time comparison."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        means = [self.df[self.df['version_strategy'] == s]['wall_clock_time_sec'].mean() 
                for s in strategies]
        stds = [self.df[self.df['version_strategy'] == s]['wall_clock_time_sec'].std() 
               for s in strategies]
        
        x_pos = np.arange(len(strategies))
        bars = ax.bar(x_pos, means, yerr=stds, capsize=5,
                     color=colors, alpha=0.8, edgecolor='black', linewidth=1.2,
                     error_kw={'linewidth': 2, 'ecolor': 'darkred'})
        
        # Labels
        ax.set_ylabel('Execution Time (seconds)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('Execution Time Comparison by Strategy', fontweight='bold', fontsize=15, pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in strategies], 
                          rotation=45, ha='right', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Value labels
        for bar, mean, std in zip(bars, means, stds):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + std + 2,
                   f'{mean:.1f}s',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '01_execution_time.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '01_execution_time.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_throughput(self):
        """Plot 2: Throughput comparison."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        means = [self.df[self.df['version_strategy'] == s]['throughput_mb_per_sec'].mean() 
                for s in strategies]
        stds = [self.df[self.df['version_strategy'] == s]['throughput_mb_per_sec'].std() 
               for s in strategies]
        
        x_pos = np.arange(len(strategies))
        bars = ax.bar(x_pos, means, yerr=stds, capsize=5,
                     color=colors, alpha=0.8, edgecolor='black', linewidth=1.2,
                     error_kw={'linewidth': 2, 'ecolor': 'darkred'})
        
        ax.set_ylabel('Throughput (MB/s)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('Processing Throughput by Strategy', fontweight='bold', fontsize=15, pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in strategies], 
                          rotation=45, ha='right', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        for bar, mean in zip(bars, means):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{mean:.2f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '02_throughput.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '02_throughput.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_memory_usage(self):
        """Plot 3: Memory usage."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        means = [self.df[self.df['version_strategy'] == s]['peak_memory_mb'].mean() 
                for s in strategies]
        
        x_pos = np.arange(len(strategies))
        bars = ax.barh(x_pos, means, color=colors, alpha=0.8, 
                      edgecolor='black', linewidth=1.2)
        
        ax.set_xlabel('Peak Memory (MB)', fontweight='bold', fontsize=13)
        ax.set_ylabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('Memory Consumption by Strategy', fontweight='bold', fontsize=15, pad=15)
        ax.set_yticks(x_pos)
        ax.set_yticklabels([s.replace('_', ' ').title() for s in strategies], fontsize=11)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        for bar, mean in zip(bars, means):
            width = bar.get_width()
            ax.text(width + 20, bar.get_y() + bar.get_height()/2.,
                   f'{mean:.0f} MB',
                   ha='left', va='center', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '03_memory_usage.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '03_memory_usage.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_cpu_efficiency(self):
        """Plot 4: CPU efficiency."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        means = [self.df[self.df['version_strategy'] == s]['cpu_efficiency'].mean() * 100 
                for s in strategies]
        
        x_pos = np.arange(len(strategies))
        bars = ax.bar(x_pos, means, color=colors, alpha=0.8, 
                     edgecolor='black', linewidth=1.2)
        
        ax.axhline(y=100, color='red', linestyle='--', linewidth=2, alpha=0.5, label='100% Efficient')
        ax.set_ylabel('CPU Efficiency (%)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('CPU Utilization Efficiency by Strategy', fontweight='bold', fontsize=15, pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in strategies], 
                          rotation=45, ha='right', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.legend(fontsize=10)
        
        for bar, mean in zip(bars, means):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{mean:.1f}%',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '04_cpu_efficiency.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '04_cpu_efficiency.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_io_wait(self):
        """Plot 5: I/O wait."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        means = [self.df[self.df['version_strategy'] == s]['io_wait_percent'].mean() 
                for s in strategies]
        
        x_pos = np.arange(len(strategies))
        bars = ax.barh(x_pos, means, color=colors, alpha=0.8, 
                      edgecolor='black', linewidth=1.2)
        
        ax.axvline(x=50, color='red', linestyle='--', linewidth=2, alpha=0.5, label='50% Threshold')
        ax.set_xlabel('I/O Wait (%)', fontweight='bold', fontsize=13)
        ax.set_ylabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('I/O Wait Time by Strategy', fontweight='bold', fontsize=15, pad=15)
        ax.set_yticks(x_pos)
        ax.set_yticklabels([s.replace('_', ' ').title() for s in strategies], fontsize=11)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        ax.legend(fontsize=10)
        
        for bar, mean in zip(bars, means):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height()/2.,
                   f'{mean:.1f}%',
                   ha='left', va='center', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '05_io_wait.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '05_io_wait.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_time_distribution(self):
        """Plot 6: Time distribution (violin plot)."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        data = [self.df[self.df['version_strategy'] == s]['wall_clock_time_sec'].values 
                for s in strategies]
        
        parts = ax.violinplot(data, positions=range(len(strategies)), 
                             widths=0.7, showmeans=True, showmedians=True)
        
        for pc, color in zip(parts['bodies'], colors):
            pc.set_facecolor(color)
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
            pc.set_linewidth(1.5)
        
        ax.set_ylabel('Execution Time (seconds)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('Execution Time Distribution by Strategy', fontweight='bold', fontsize=15, pad=15)
        ax.set_xticks(range(len(strategies)))
        ax.set_xticklabels([s.replace('_', ' ').title() for s in strategies], 
                          rotation=45, ha='right', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '06_time_distribution.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '06_time_distribution.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_performance_matrix(self):
        """Plot 7: Performance matrix heatmap."""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        pivot = self.df.pivot_table(
            values='wall_clock_time_sec',
            index='version_strategy',
            columns='file_extension',
            aggfunc='mean'
        )
        
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax,
                   cbar_kws={'label': 'Execution Time (seconds)'},
                   linewidths=2, linecolor='white',
                   annot_kws={'fontsize': 12, 'fontweight': 'bold'})
        
        ax.set_title('Performance Matrix: Strategy × File Type', fontweight='bold', fontsize=15, pad=15)
        ax.set_xlabel('File Extension', fontweight='bold', fontsize=13)
        ax.set_ylabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_xticklabels([f'.{col.upper()}' for col in pivot.columns], 
                          rotation=45, ha='right', fontsize=11)
        ax.set_yticklabels([idx.replace('_', ' ').title() for idx in pivot.index], 
                          rotation=0, fontsize=11)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '07_performance_matrix.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '07_performance_matrix.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_efficiency_scatter(self):
        """Plot 8: Efficiency scatter plot."""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        for strategy, color in zip(strategies, colors):
            data = self.df[self.df['version_strategy'] == strategy]
            ax.scatter(data['wall_clock_time_sec'], data['cpu_efficiency'] * 100,
                      label=strategy.replace('_', ' ').title(),
                      alpha=0.7, s=100, c=[color], edgecolors='black', linewidth=1)
        
        ax.axhline(y=100, color='red', linestyle='--', linewidth=2, alpha=0.5, label='100% Efficient')
        ax.set_xlabel('Execution Time (seconds)', fontweight='bold', fontsize=13)
        ax.set_ylabel('CPU Efficiency (%)', fontweight='bold', fontsize=13)
        ax.set_title('CPU Efficiency vs Execution Time', fontweight='bold', fontsize=15, pad=15)
        ax.legend(fontsize=10, loc='best', framealpha=0.9)
        ax.grid(alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '08_efficiency_scatter.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '08_efficiency_scatter.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_context_switches(self):
        """Plot 9: Context switches analysis."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        vol_ctx = [self.df[self.df['version_strategy'] == s]['voluntary_context_switches'].mean() 
                   for s in strategies]
        invol_ctx = [self.df[self.df['version_strategy'] == s]['involuntary_context_switches'].mean() 
                     for s in strategies]
        
        x_pos = np.arange(len(strategies))
        width = 0.35
        
        bars1 = ax.bar(x_pos - width/2, vol_ctx, width, label='Voluntary',
                      color=colors[0], alpha=0.8, edgecolor='black', linewidth=1)
        bars2 = ax.bar(x_pos + width/2, invol_ctx, width, label='Involuntary',
                      color=colors[1], alpha=0.8, edgecolor='black', linewidth=1)
        
        ax.set_ylabel('Context Switches (count)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('Context Switches: Voluntary vs Involuntary', fontweight='bold', fontsize=15, pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in strategies], 
                          rotation=45, ha='right', fontsize=11)
        ax.set_yscale('log')
        ax.legend(fontsize=11, loc='best')
        ax.grid(axis='y', alpha=0.3, linestyle='--', which='both')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '09_context_switches.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '09_context_switches.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_file_io(self):
        """Plot 10: File system I/O operations."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        inputs = [self.df[self.df['version_strategy'] == s]['file_system_inputs'].mean() 
                 for s in strategies]
        outputs = [self.df[self.df['version_strategy'] == s]['file_system_outputs'].mean() 
                  for s in strategies]
        
        x_pos = np.arange(len(strategies))
        width = 0.35
        
        bars1 = ax.bar(x_pos - width/2, inputs, width, label='Inputs',
                      color=colors[2], alpha=0.8, edgecolor='black', linewidth=1)
        bars2 = ax.bar(x_pos + width/2, outputs, width, label='Outputs',
                      color=colors[3], alpha=0.8, edgecolor='black', linewidth=1)
        
        ax.set_ylabel('File System Operations (count)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('File System I/O Operations', fontweight='bold', fontsize=15, pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in strategies], 
                          rotation=45, ha='right', fontsize=11)
        ax.set_yscale('log')
        ax.legend(fontsize=11, loc='best')
        ax.grid(axis='y', alpha=0.3, linestyle='--', which='both')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '10_file_io.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '10_file_io.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_memory_efficiency(self):
        """Plot 11: Memory efficiency (MB/s)."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        if 'memory_efficiency_mb_per_sec' in self.df.columns:
            means = [self.df[self.df['version_strategy'] == s]['memory_efficiency_mb_per_sec'].mean() 
                    for s in strategies]
        else:
            # Calculate memory efficiency as throughput / peak_memory
            means = [(self.df[self.df['version_strategy'] == s]['throughput_mb_per_sec'].mean() / 
                     self.df[self.df['version_strategy'] == s]['peak_memory_mb'].mean())
                    for s in strategies]
        
        x_pos = np.arange(len(strategies))
        bars = ax.bar(x_pos, means, color=colors, alpha=0.8, 
                     edgecolor='black', linewidth=1.2)
        
        ax.set_ylabel('Memory Efficiency (MB/s per MB)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Strategy', fontweight='bold', fontsize=13)
        ax.set_title('Memory Efficiency: Throughput per Memory Used', fontweight='bold', fontsize=15, pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in strategies], 
                          rotation=45, ha='right', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        for bar, mean in zip(bars, means):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.0001,
                   f'{mean:.4f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '11_memory_efficiency.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '11_memory_efficiency.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def plot_throughput_vs_size(self):
        """Plot 12: Throughput vs file size scatter."""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        strategies = sorted(self.df['version_strategy'].unique())
        colors = sns.color_palette('Set2', len(strategies))
        
        for strategy, color in zip(strategies, colors):
            data = self.df[self.df['version_strategy'] == strategy]
            ax.scatter(data['file_size_mb'], data['throughput_mb_per_sec'],
                      label=strategy.replace('_', ' ').title(),
                      alpha=0.7, s=100, c=[color], edgecolors='black', linewidth=1)
        
        ax.set_xlabel('File Size (MB)', fontweight='bold', fontsize=13)
        ax.set_ylabel('Throughput (MB/s)', fontweight='bold', fontsize=13)
        ax.set_title('Throughput vs File Size by Strategy', fontweight='bold', fontsize=15, pad=15)
        ax.legend(fontsize=10, loc='best', framealpha=0.9)
        ax.grid(alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '12_throughput_vs_size.png', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / '12_throughput_vs_size.pdf', bbox_inches='tight')
        plt.close()
        
        return 1
    
    def create_markdown_report(self):
        """Create comprehensive Markdown report with all visualizations."""
        md_content = f"""# Benchmark Analysis Report - Individual Visualizations

**Generated:** {self.analyzer.data_path.name}  
**Analysis Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

- **Total Records:** {len(self.df)}
- **Strategies Analyzed:** {', '.join(sorted(self.df['version_strategy'].unique()))}
- **File Types:** {', '.join(sorted(self.df['file_extension'].unique()))}

> 📌 **Note:** This report contains individual, separated graphs for better visualization and analysis. Each metric is presented in its own dedicated plot.

---

## Table of Contents

1. [Performance Metrics](#performance-metrics)
2. [Resource Utilization](#resource-utilization)
3. [Efficiency Analysis](#efficiency-analysis)
4. [Distribution Analysis](#distribution-analysis)
5. [Recommendations](#recommendations)

---

## Performance Metrics

### 1. Execution Time Comparison

![Execution Time](01_execution_time.png)

**Description:** Average execution time for each strategy with error bars showing standard deviation.

**Key Findings:**
- Comparison of execution times across all strategies
- Error bars show variability in measurements
- Lower execution time indicates better performance
- Ideal for identifying the fastest strategy

---

### 2. Processing Throughput

![Throughput](02_throughput.png)

**Description:** Data processing speed measured in MB/s for each strategy.

**Key Findings:**
- Throughput measured in MB/s
- Higher throughput indicates better performance
- Shows data processing efficiency
- Helps identify strategies optimized for large files

---

## Resource Utilization

### 3. Memory Consumption

![Memory Usage](03_memory_usage.png)

**Description:** Peak memory usage in MB for each strategy.

**Key Findings:**
- Peak memory usage per strategy
- Important for resource planning
- Lower memory usage is preferred for constrained environments
- Horizontal bars for easy comparison

---

### 4. CPU Utilization Efficiency

![CPU Efficiency](04_cpu_efficiency.png)

**Description:** Percentage of CPU time utilized effectively (100% = fully CPU-bound).

**Key Findings:**
- Percentage of CPU time utilized effectively
- 100% indicates full CPU utilization
- Values near 100% show CPU-bound operations
- Lower values suggest I/O or other bottlenecks

---

### 5. I/O Wait Time

![I/O Wait](05_io_wait.png)

**Description:** Percentage of time spent waiting for I/O operations.

**Key Findings:**
- Percentage of time waiting for I/O operations
- High values (>50%) indicate I/O bottlenecks
- Lower is better for performance
- Red line shows 50% threshold

---

## Efficiency Analysis

### 6. Execution Time Distribution

![Time Distribution](06_time_distribution.png)

**Description:** Violin plot showing the distribution of execution times.

**Key Findings:**
- Violin plot showing execution time distribution
- Inner markings show median and mean
- Width indicates data density
- Reveals performance consistency

---

### 7. Performance Matrix

![Performance Matrix](07_performance_matrix.png)

**Description:** Heatmap showing performance across different file types and strategies.

**Key Findings:**
- Heatmap showing performance across file types
- Darker colors indicate longer execution times
- Useful for identifying format-specific issues
- Quick overview of strategy-file type combinations

---

### 8. CPU Efficiency vs Execution Time

![Efficiency Scatter](08_efficiency_scatter.png)

**Description:** Scatter plot showing the relationship between execution time and CPU efficiency.

**Key Findings:**
- Relationship between execution time and CPU efficiency
- Scatter plot shows individual data points
- Helps identify optimal strategy balance
- Red line marks 100% efficiency threshold

---

## System Resources Analysis

### 9. Context Switches

![Context Switches](09_context_switches.png)

**Description:** Voluntary and involuntary context switches by strategy.

**Key Findings:**
- Voluntary switches: process yields control
- Involuntary switches: process is interrupted
- Higher values may indicate contention
- Logarithmic scale for better visualization

---

### 10. File System I/O Operations

![File I/O](10_file_io.png)

**Description:** Number of file system input and output operations.

**Key Findings:**
- Inputs: read operations from disk
- Outputs: write operations to disk
- Lower values indicate less I/O overhead
- Logarithmic scale for comparison

---

### 11. Memory Efficiency

![Memory Efficiency](11_memory_efficiency.png)

**Description:** Throughput per MB of memory used (efficiency metric).

**Key Findings:**
- Throughput per MB of memory used
- Higher values indicate better memory efficiency
- Balances speed with memory footprint
- Useful for memory-constrained environments

---

### 12. Throughput vs File Size

![Throughput vs Size](12_throughput_vs_size.png)

**Description:** Scatter plot showing throughput performance at different file sizes.

**Key Findings:**
- Relationship between file size and throughput
- Identifies strategies that scale well
- Shows performance degradation patterns
- Helps select strategy based on file size

---

## Recommendations

Based on the comprehensive analysis:

### 🏆 Best Overall Performance
Check **Plot 1: Execution Time Comparison** to identify the fastest strategy.

### ⚡ Most CPU Efficient
Review **Plot 4: CPU Efficiency** to find strategies with optimal CPU utilization.

### 💾 Lowest Memory Footprint
Analyze **Plot 3: Memory Usage** for memory-constrained environments.

### 🔧 I/O Optimization
Check **Plot 5: I/O Wait** to identify strategies with minimal I/O bottlenecks.

### 📊 Balanced Performance
Review **Plot 11: Memory Efficiency** for the best balance between speed and resources.

### 📈 Scalability
Examine **Plot 12: Throughput vs Size** to understand how strategies scale with file size.

---

## Statistical Details

For detailed statistical analysis, please refer to the text reports in the parent directory:

- `executive_summary.txt` - High-level overview
- `strategy_comparison.txt` - Strategy performance comparison
- `resource_analysis.txt` - Resource utilization details
- `statistical_analysis.txt` - Statistical tests and significance

---

## Notes

- All plots are available in **PNG** (high resolution) and **PDF** (vector) formats
- PNG files: 300 DPI for publication quality
- PDF files: Scalable vector graphics for presentations
- Each plot is designed to be clear and readable when viewed individually
- No overlapping labels or cramped layouts

---

*Report generated by Advanced Benchmark Analysis Tool*  
*Individual Visualization Mode - Clean, separated plots for better analysis*
"""
        
        md_path = self.output_dir / 'README.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"   ✅ Created visualization report: {md_path}")
