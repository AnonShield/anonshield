"""
Scientific Visualization Module for AnonShield Benchmark

Modular, publication-quality visualization system following SOLID principles.
"""

from .config import VisualizationConfig, ColorScheme, FigureSize, Typography, PlotStyle
from .statistics import (
    StatisticalAnalyzer,
    RegressionAnalyzer,
    EffectSizeCalculator,
    VarianceAnalyzer,
    CorrelationAnalyzer,
)
from .charts import (
    ChartFactory,
    PerformanceCharts,
    StatisticalCharts,
    RegressionCharts,
    DistributionCharts,
    ResourceCharts,
    ScalabilityCharts,
    CorrelationCharts,
    VarianceCharts,
)

__all__ = [
    'VisualizationConfig',
    'ColorScheme',
    'FigureSize',
    'Typography',
    'PlotStyle',
    'StatisticalAnalyzer',
    'RegressionAnalyzer',
    'EffectSizeCalculator',
    'VarianceAnalyzer',
    'CorrelationAnalyzer',
    'ChartFactory',
    'PerformanceCharts',
    'StatisticalCharts',
    'RegressionCharts',
    'DistributionCharts',
    'ResourceCharts',
    'ScalabilityCharts',
    'CorrelationCharts',
    'VarianceCharts',
]

__version__ = '3.1.0'
