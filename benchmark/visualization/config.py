#!/usr/bin/env python3
"""
Publication-Quality Visualization Configuration
Scientific standards for high-impact journals and conferences.

Author: AnonShield Team
Version: 3.0 - Refactored for scientific rigor
"""

from dataclasses import dataclass
from typing import Tuple, Dict
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class ColorScheme:
    """Colorblind-safe color schemes (Wong 2011, Nature Methods).

    Reference: https://www.nature.com/articles/nmeth.1618
    """
    # Wong palette - optimized for colorblindness
    WONG_BLACK: str = '#000000'
    WONG_ORANGE: str = '#E69F00'
    WONG_SKY_BLUE: str = '#56B4E9'
    WONG_GREEN: str = '#009E73'
    WONG_YELLOW: str = '#F0E442'
    WONG_BLUE: str = '#0072B2'
    WONG_VERMILLION: str = '#D55E00'
    WONG_PURPLE: str = '#CC79A7'

    # Semantic colors
    PRIMARY: str = '#0072B2'      # Blue - main comparisons
    SECONDARY: str = '#009E73'    # Green - secondary metrics
    ACCENT: str = '#D55E00'       # Vermillion - highlights
    WARNING: str = '#E69F00'      # Orange - warnings
    ERROR: str = '#CC0000'        # Red - errors/failures
    NEUTRAL: str = '#666666'      # Gray - neutral/baseline

    @classmethod
    def get_categorical_palette(cls, n: int = 8) -> list:
        """Get categorical palette for N categories."""
        base_colors = [
            cls.WONG_BLUE,
            cls.WONG_ORANGE,
            cls.WONG_GREEN,
            cls.WONG_VERMILLION,
            cls.WONG_SKY_BLUE,
            cls.WONG_PURPLE,
            cls.WONG_YELLOW,
            cls.WONG_BLACK
        ]
        return base_colors[:n] if n <= 8 else base_colors * (n // 8 + 1)

    @classmethod
    def get_sequential_colormap(cls, reverse: bool = False) -> str:
        """Get sequential colormap for heatmaps."""
        # Using matplotlib's viridis (colorblind-safe)
        return 'viridis_r' if reverse else 'viridis'

    @classmethod
    def get_diverging_colormap(cls) -> str:
        """Get diverging colormap for deviations."""
        # RdBu is reasonably colorblind-safe
        return 'RdBu_r'

    @classmethod
    def get_version_strategy_colors(cls) -> Dict[str, str]:
        """Get consistent color mapping for version+strategy combinations.

        This ensures the same version+strategy always gets the same color
        across all visualizations.
        """
        return {
            # Version 1.0
            '1.0_default': cls.WONG_BLUE,

            # Version 2.0
            '2.0_default': cls.WONG_PURPLE,

            # AnonShield (Version 3.0)
            'AnonShield_filtered': cls.WONG_YELLOW,
            'AnonShield_hybrid': cls.WONG_GREEN,
            'AnonShield_presidio': cls.WONG_ORANGE,
            'AnonShield_standalone': cls.WONG_SKY_BLUE,
        }

    @classmethod
    def get_version_display_names(cls) -> Dict[str, str]:
        """Human-readable display names for version_strategy labels (paper branding)."""
        return {
            '1.0_default':         'AnonLFI v1.0',
            '2.0_default':         'AnonLFI v2.0',
            'AnonShield_filtered':  'AnonShield filtered',
            'AnonShield_hybrid':    'AnonShield hybrid',
            'AnonShield_presidio':  'AnonShield presidio',
            'AnonShield_standalone':'AnonShield standalone',
        }



@dataclass(frozen=True)
class FigureSize:
    """Standard figure sizes for scientific publications.

    Based on common journal requirements:
    - Nature/Science: 89mm (single), 183mm (double)
    - IEEE: 3.5" (single), 7" (double)
    - PLOS: 2.63" (single), 5.5" (double)

    Using IEEE standards as default.
    """
    # Single column (inches) - INCREASED for better readability
    SINGLE_COLUMN_WIDTH: float = 5.0  # Was 3.5
    SINGLE_COLUMN_HEIGHT: float = 3.75  # Was 2.625
    SINGLE_SQUARE: Tuple[float, float] = (5.0, 5.0)  # Was (3.5, 3.5)
    SINGLE_WIDE: Tuple[float, float] = (5.0, 3.0)  # Was (3.5, 2.0)
    SINGLE_TALL: Tuple[float, float] = (5.0, 7.0)  # Was (3.5, 5.0)

    # Double column (inches) - INCREASED for better readability
    DOUBLE_COLUMN_WIDTH: float = 10.0  # Was 7.0
    DOUBLE_COLUMN_HEIGHT: float = 7.5  # Was 5.25
    DOUBLE_SQUARE: Tuple[float, float] = (10.0, 10.0)  # Was (7.0, 7.0)
    DOUBLE_WIDE: Tuple[float, float] = (10.0, 6.0)  # Was (7.0, 4.0)
    DOUBLE_TALL: Tuple[float, float] = (10.0, 12.0)  # Was (7.0, 9.0)

    # Full page - INCREASED
    FULL_PAGE: Tuple[float, float] = (10.0, 13.0)  # Was (7.0, 9.5)

    # Presentation (16:9) - INCREASED
    PRESENTATION: Tuple[float, float] = (14, 7.875)  # Was (10, 5.625)
    PRESENTATION_LARGE: Tuple[float, float] = (16, 9.0)  # Was (12, 6.75)

    # Legacy sizes (for backward compatibility)
    LEGACY_WIDE: Tuple[float, float] = (16, 6)
    LEGACY_SQUARE: Tuple[float, float] = (12, 10)
    LEGACY_TALL: Tuple[float, float] = (12, 14)


@dataclass(frozen=True)
class Typography:
    """Typography settings for publication-quality figures."""
    # Font family (use system fonts for compatibility)
    FAMILY_SERIF: str = 'DejaVu Serif'
    FAMILY_SANS: str = 'DejaVu Sans'
    FAMILY_MONO: str = 'DejaVu Sans Mono'

    # Font sizes (points) - based on Nature guidelines
    SIZE_TINY: int = 6
    SIZE_SMALL: int = 7
    SIZE_BASE: int = 8
    SIZE_MEDIUM: int = 9
    SIZE_LARGE: int = 10
    SIZE_XLARGE: int = 11
    SIZE_TITLE: int = 12

    # Specific element sizes
    SIZE_AXIS_LABEL: int = 9
    SIZE_AXIS_TICK: int = 8
    SIZE_LEGEND: int = 8
    SIZE_ANNOTATION: int = 7
    SIZE_SUPTITLE: int = 11


@dataclass(frozen=True)
class PlotStyle:
    """Style parameters for plot elements."""
    # DPI settings
    DPI_SCREEN: int = 100
    DPI_PRINT: int = 300
    DPI_HIGH: int = 600

    # Line styles
    LINE_WIDTH_THIN: float = 0.5
    LINE_WIDTH_NORMAL: float = 1.0
    LINE_WIDTH_THICK: float = 1.5
    LINE_WIDTH_HEAVY: float = 2.0

    # Marker styles
    MARKER_SIZE_SMALL: float = 3
    MARKER_SIZE_NORMAL: float = 6
    MARKER_SIZE_LARGE: float = 10

    # Grid
    GRID_ALPHA: float = 0.3
    GRID_LINESTYLE: str = ':'
    GRID_LINEWIDTH: float = 0.5

    # Transparency
    ALPHA_FILL: float = 0.3
    ALPHA_MARKER: float = 0.7
    ALPHA_LINE: float = 0.8

    # Error bars
    ERROR_BAR_CAPSIZE: float = 3
    ERROR_BAR_LINEWIDTH: float = 1.0

    # Statistical significance
    @property
    def SIGNIFICANCE_LEVELS(self) -> Dict[str, float]:
        return {
            'ns': 1.0,       # p >= 0.05 (not significant)
            '*': 0.05,       # p < 0.05
            '**': 0.01,      # p < 0.01
            '***': 0.001,    # p < 0.001
            '****': 0.0001   # p < 0.0001
        }


class VisualizationConfig:
    """Master configuration for all visualizations.

    Usage:
        config = VisualizationConfig(mode='paper')
        config.apply()
    """

    def __init__(self, mode: str = 'paper'):
        """Initialize configuration.

        Args:
            mode: 'paper' (publication), 'presentation' (slides), 'screen' (display)
        """
        self.mode = mode
        self.colors = ColorScheme()
        self.sizes = FigureSize()
        self.typography = Typography()
        self.style = PlotStyle()

    def apply(self):
        """Apply configuration to matplotlib."""
        # Set style based on mode
        if self.mode == 'paper':
            plt.style.use('seaborn-v0_8-paper')
            dpi = self.style.DPI_PRINT
            font_family = self.typography.FAMILY_SANS
        elif self.mode == 'presentation':
            plt.style.use('seaborn-v0_8-talk')
            dpi = self.style.DPI_SCREEN
            font_family = self.typography.FAMILY_SANS
        else:  # screen
            plt.style.use('seaborn-v0_8-whitegrid')
            dpi = self.style.DPI_SCREEN
            font_family = self.typography.FAMILY_SANS

        # Apply comprehensive rcParams
        plt.rcParams.update({
            # Figure
            'figure.dpi': self.style.DPI_SCREEN,
            'savefig.dpi': dpi,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.05,
            'savefig.transparent': False,

            # Font
            'font.family': font_family,
            'font.size': self.typography.SIZE_BASE,

            # Axes
            'axes.labelsize': self.typography.SIZE_AXIS_LABEL,
            'axes.titlesize': self.typography.SIZE_TITLE,
            'axes.titleweight': 'bold',
            'axes.labelweight': 'normal',
            'axes.linewidth': self.style.LINE_WIDTH_NORMAL,
            'axes.edgecolor': '#333333',
            'axes.grid': True,
            'axes.axisbelow': True,
            'axes.spines.top': False,
            'axes.spines.right': False,

            # Ticks
            'xtick.labelsize': self.typography.SIZE_AXIS_TICK,
            'ytick.labelsize': self.typography.SIZE_AXIS_TICK,
            'xtick.direction': 'out',
            'ytick.direction': 'out',
            'xtick.major.width': self.style.LINE_WIDTH_NORMAL,
            'ytick.major.width': self.style.LINE_WIDTH_NORMAL,

            # Grid
            'grid.alpha': self.style.GRID_ALPHA,
            'grid.linestyle': self.style.GRID_LINESTYLE,
            'grid.linewidth': self.style.GRID_LINEWIDTH,

            # Legend
            'legend.fontsize': self.typography.SIZE_LEGEND,
            'legend.frameon': True,
            'legend.framealpha': 0.9,
            'legend.edgecolor': '#CCCCCC',
            'legend.fancybox': False,

            # Lines
            'lines.linewidth': self.style.LINE_WIDTH_NORMAL,
            'lines.markersize': self.style.MARKER_SIZE_NORMAL,

            # Error bars
            'errorbar.capsize': self.style.ERROR_BAR_CAPSIZE,

            # Math text
            'mathtext.default': 'regular',
        })

    def get_figure_size(self, layout: str = 'double_wide') -> Tuple[float, float]:
        """Get figure size for specific layout.

        Args:
            layout: 'single', 'single_wide', 'double', 'double_wide',
                   'double_square', 'full_page', 'presentation'
        """
        size_map = {
            'single': (self.sizes.SINGLE_COLUMN_WIDTH, self.sizes.SINGLE_COLUMN_HEIGHT),
            'single_wide': self.sizes.SINGLE_WIDE,
            'single_square': self.sizes.SINGLE_SQUARE,
            'single_tall': self.sizes.SINGLE_TALL,
            'double': (self.sizes.DOUBLE_COLUMN_WIDTH, self.sizes.DOUBLE_COLUMN_HEIGHT),
            'double_wide': self.sizes.DOUBLE_WIDE,
            'double_square': self.sizes.DOUBLE_SQUARE,
            'double_tall': self.sizes.DOUBLE_TALL,
            'full_page': self.sizes.FULL_PAGE,
            'presentation': self.sizes.PRESENTATION,
            'presentation_large': self.sizes.PRESENTATION_LARGE,
        }
        return size_map.get(layout, self.sizes.DOUBLE_WIDE)

    def get_colors(self, n: int = 8, strategies: list = None) -> list:
        """Get N categorical colors.

        Args:
            n: Number of colors needed
            strategies: Optional list of version_strategy names for consistent mapping

        Returns:
            List of colors (hex strings)
        """
        if strategies:
            # Use consistent color mapping for version+strategy
            color_map = self.colors.get_version_strategy_colors()
            return [color_map.get(s, self.colors.get_categorical_palette(n)[i % 8])
                    for i, s in enumerate(strategies)]
        return self.colors.get_categorical_palette(n)

    def get_version_display_names(self) -> Dict[str, str]:
        """Human-readable display names for version_strategy labels (paper branding)."""
        return ColorScheme.get_version_display_names()

    @staticmethod
    def sort_strategies_by_version(strategies: list) -> list:
        """Sort strategies by version first, then alphabetically.

        Args:
            strategies: List of version_strategy strings (e.g., ['3.0_standalone', '1.0_default'])

        Returns:
            Sorted list grouped by version (e.g., ['1.0_default', '2.0_default', '3.0_filtered', ...])
        """
        def parse_version(s: str):
            """Extract version and strategy from version_strategy string."""
            parts = s.split('_', 1)
            if len(parts) == 2:
                try:
                    version = float(parts[0])
                    strategy = parts[1]
                    return (version, strategy)
                except ValueError:
                    pass
            return (999, s)  # Fallback for unparseable strings

        return sorted(strategies, key=parse_version)

    def save_figure(self, fig, filepath: str, dpi: int | None = None):
        """Save figure with proper settings.

        Args:
            fig: Matplotlib figure
            filepath: Output path
            dpi: Override DPI (default: from mode)
        """
        save_dpi = dpi if dpi is not None else (
            self.style.DPI_PRINT if self.mode == 'paper' else self.style.DPI_SCREEN
        )

        # Save as PNG and PDF for flexibility
        base_path = filepath.rsplit('.', 1)[0] if '.' in filepath else filepath

        fig.savefig(f"{base_path}.png", dpi=save_dpi, bbox_inches='tight', pad_inches=0.05)
        fig.savefig(f"{base_path}.pdf", bbox_inches='tight', pad_inches=0.05)

        plt.close(fig)
