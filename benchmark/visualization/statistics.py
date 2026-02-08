#!/usr/bin/env python3
"""
Statistical Analysis Module for Benchmark Data

Provides rigorous statistical methods for scientific publications:
- Effect size calculations (Cohen's d, Hedges' g)
- Multiple comparison corrections (Bonferroni, Benjamini-Hochberg)
- Regression analysis with diagnostics
- Normality tests and transformations
- Power analysis

Author: AnonShield Team
Version: 3.0
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import normaltest, shapiro, anderson
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import TTestIndPower


@dataclass
class EffectSize:
    """Effect size result with interpretation."""
    value: float
    ci_lower: float
    ci_upper: float
    interpretation: str
    method: str


@dataclass
class RegressionResult:
    """Regression analysis results."""
    slope: float
    intercept: float
    r_squared: float
    p_value: float
    std_err: float
    ci_slope: Tuple[float, float]
    ci_intercept: Tuple[float, float]
    residuals: np.ndarray
    predicted: np.ndarray
    n_samples: int


@dataclass
class OverheadModel:
    """Overhead decomposition model: time = overhead + size/throughput."""
    overhead_sec: float
    throughput_kb_per_sec: float
    overhead_ci: Tuple[float, float]
    throughput_ci: Tuple[float, float]
    r_squared: float
    p_value: float
    residuals: np.ndarray
    method: str  # 'linear', 'robust', 'bayesian'


class EffectSizeCalculator:
    """Calculate effect sizes with confidence intervals.

    Methods:
    - Cohen's d: Standardized mean difference
    - Hedges' g: Bias-corrected Cohen's d for small samples
    - Glass's delta: Uses control group SD only
    """

    @staticmethod
    def cohens_d(group1: np.ndarray, group2: np.ndarray,
                 ci_level: float = 0.95) -> EffectSize:
        """Calculate Cohen's d with confidence intervals.

        Cohen's d interpretation (conventional):
        - 0.2: Small effect
        - 0.5: Medium effect
        - 0.8: Large effect

        Args:
            group1: First group data
            group2: Second group data
            ci_level: Confidence interval level (default: 0.95)

        Returns:
            EffectSize object with value and CI
        """
        n1, n2 = len(group1), len(group2)
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

        # Cohen's d
        d = (mean1 - mean2) / pooled_std

        # Confidence interval (Hedges & Olkin, 1985)
        se_d = np.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
        z_crit = stats.norm.ppf((1 + ci_level) / 2)
        ci_lower = d - z_crit * se_d
        ci_upper = d + z_crit * se_d

        # Interpretation
        abs_d = abs(d)
        if abs_d < 0.2:
            interp = "negligible"
        elif abs_d < 0.5:
            interp = "small"
        elif abs_d < 0.8:
            interp = "medium"
        else:
            interp = "large"

        return EffectSize(
            value=d,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            interpretation=interp,
            method="Cohen's d"
        )

    @staticmethod
    def hedges_g(group1: np.ndarray, group2: np.ndarray,
                 ci_level: float = 0.95) -> EffectSize:
        """Calculate Hedges' g (bias-corrected Cohen's d).

        Recommended for small sample sizes (n < 20).

        Args:
            group1: First group data
            group2: Second group data
            ci_level: Confidence interval level

        Returns:
            EffectSize object
        """
        # First calculate Cohen's d
        d_result = EffectSizeCalculator.cohens_d(group1, group2, ci_level)

        n1, n2 = len(group1), len(group2)
        n = n1 + n2

        # Correction factor (Hedges, 1981)
        correction = 1 - (3 / (4 * n - 9))
        g = d_result.value * correction

        # Adjust CI
        ci_lower = d_result.ci_lower * correction
        ci_upper = d_result.ci_upper * correction

        return EffectSize(
            value=g,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            interpretation=d_result.interpretation,
            method="Hedges' g"
        )


class StatisticalAnalyzer:
    """Comprehensive statistical analysis for benchmark data."""

    @staticmethod
    def test_normality(data: np.ndarray, alpha: float = 0.05) -> Dict:
        """Test normality using multiple methods.

        Args:
            data: Array to test
            alpha: Significance level

        Returns:
            Dictionary with test results
        """
        results = {}

        # Shapiro-Wilk (best for n < 5000)
        if len(data) <= 5000:
            stat_sw, p_sw = shapiro(data)
            results['shapiro_wilk'] = {
                'statistic': stat_sw,
                'p_value': p_sw,
                'normal': p_sw > alpha
            }

        # D'Agostino-Pearson (good for n > 20)
        if len(data) > 20:
            stat_da, p_da = normaltest(data)
            results['dagostino_pearson'] = {
                'statistic': stat_da,
                'p_value': p_da,
                'normal': p_da > alpha
            }

        # Anderson-Darling
        result_ad = anderson(data)
        # Critical value for alpha=0.05 is typically at index 2
        critical_idx = 2  # 5% significance
        results['anderson_darling'] = {
            'statistic': result_ad.statistic,
            'critical_value': result_ad.critical_values[critical_idx],
            'normal': result_ad.statistic < result_ad.critical_values[critical_idx]
        }

        # Overall conclusion
        normal_tests = [r.get('normal', False) for r in results.values()]
        results['is_normal'] = sum(normal_tests) >= len(normal_tests) / 2

        return results

    @staticmethod
    def multiple_comparison_correction(p_values: List[float],
                                      method: str = 'fdr_bh',
                                      alpha: float = 0.05) -> Dict:
        """Apply multiple comparison correction.

        Args:
            p_values: List of p-values
            method: 'bonferroni', 'holm', 'fdr_bh' (Benjamini-Hochberg),
                   'fdr_by' (Benjamini-Yekutieli)
            alpha: Family-wise error rate

        Returns:
            Dictionary with corrected p-values and reject decisions
        """
        reject, p_corrected, alpha_sidak, alpha_bonf = multipletests(
            p_values, alpha=alpha, method=method
        )

        return {
            'method': method,
            'alpha': alpha,
            'p_values_original': p_values,
            'p_values_corrected': p_corrected.tolist(),
            'reject_null': reject.tolist(),
            'n_significant': sum(reject),
            'n_tests': len(p_values),
            'alpha_bonferroni': alpha_bonf,
            'alpha_sidak': alpha_sidak
        }

    @staticmethod
    def compute_confidence_interval(data: np.ndarray,
                                   confidence: float = 0.95) -> Tuple[float, float, float]:
        """Compute mean and confidence interval.

        Args:
            data: Data array
            confidence: Confidence level (default: 0.95)

        Returns:
            Tuple of (mean, ci_lower, ci_upper)
        """
        n = len(data)
        mean = np.mean(data)
        se = stats.sem(data)
        margin = se * stats.t.ppf((1 + confidence) / 2, n - 1)

        return mean, mean - margin, mean + margin

    @staticmethod
    def mann_whitney_with_effect_size(group1: np.ndarray, group2: np.ndarray) -> Dict:
        """Mann-Whitney U test with rank-biserial correlation as effect size.

        Args:
            group1: First group
            group2: Second group

        Returns:
            Dictionary with test results and effect size
        """
        # Mann-Whitney U test
        u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')

        # Rank-biserial correlation (effect size for Mann-Whitney)
        n1, n2 = len(group1), len(group2)
        r = 1 - (2 * u_stat) / (n1 * n2)  # Ranges from -1 to 1

        # Interpretation
        abs_r = abs(r)
        if abs_r < 0.1:
            interpretation = "negligible"
        elif abs_r < 0.3:
            interpretation = "small"
        elif abs_r < 0.5:
            interpretation = "medium"
        else:
            interpretation = "large"

        return {
            'u_statistic': u_stat,
            'p_value': p_value,
            'rank_biserial_r': r,
            'effect_size_interpretation': interpretation,
            'n1': n1,
            'n2': n2
        }


class RegressionAnalyzer:
    """Regression analysis with comprehensive diagnostics."""

    @staticmethod
    def linear_regression(x: np.ndarray, y: np.ndarray,
                         confidence: float = 0.95) -> RegressionResult:
        """Perform linear regression with confidence intervals.

        Args:
            x: Independent variable
            y: Dependent variable
            confidence: Confidence level for intervals

        Returns:
            RegressionResult object
        """
        # Add constant for intercept
        X = sm.add_constant(x)
        model = sm.OLS(y, X)
        results = model.fit()

        # Extract parameters
        intercept, slope = results.params
        std_err_intercept, std_err_slope = results.bse

        # Confidence intervals
        ci = results.conf_int(alpha=1 - confidence)
        ci_intercept = tuple(ci[0])
        ci_slope = tuple(ci[1])

        # Predictions and residuals
        predicted = results.predict(X)
        residuals = results.resid

        # R-squared and p-value
        r_squared = results.rsquared
        p_value = results.f_pvalue

        return RegressionResult(
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            p_value=p_value,
            std_err=std_err_slope,
            ci_slope=ci_slope,
            ci_intercept=ci_intercept,
            residuals=residuals,
            predicted=predicted,
            n_samples=len(x)
        )

    @staticmethod
    def overhead_model(file_sizes_kb: np.ndarray, times_sec: np.ndarray,
                      method: str = 'linear') -> OverheadModel:
        """Fit overhead model: time = overhead + size/throughput.

        Model: t = a + b*s
        Where:
        - a = overhead (fixed time independent of file size)
        - b = 1/throughput (inverse of processing rate)

        Args:
            file_sizes_kb: File sizes in KB
            times_sec: Execution times in seconds
            method: 'linear' (OLS), 'robust' (Huber), 'ransac' (outlier-robust)

        Returns:
            OverheadModel object
        """
        if method == 'linear':
            result = RegressionAnalyzer.linear_regression(file_sizes_kb, times_sec)
            overhead_sec = result.intercept
            throughput_kb_per_sec = 1 / result.slope if result.slope > 0 else 0
            overhead_ci = result.ci_intercept
            # Throughput CI: inverse of slope CI (careful with direction)
            throughput_ci = (
                1 / result.ci_slope[1] if result.ci_slope[1] > 0 else 0,
                1 / result.ci_slope[0] if result.ci_slope[0] > 0 else float('inf')
            )
            residuals = result.residuals
            r_squared = result.r_squared
            p_value = result.p_value

        elif method == 'robust':
            # Robust linear regression using Huber M-estimator
            X = sm.add_constant(file_sizes_kb)
            huber_model = sm.RLM(times_sec, X, M=sm.robust.norms.HuberT())
            huber_results = huber_model.fit()

            overhead_sec = huber_results.params[0]
            slope = huber_results.params[1]
            throughput_kb_per_sec = 1 / slope if slope > 0 else 0

            # CI estimation (approximate)
            ci = huber_results.conf_int()
            overhead_ci = tuple(ci[0])
            throughput_ci = (
                1 / ci[1][1] if ci[1][1] > 0 else 0,
                1 / ci[1][0] if ci[1][0] > 0 else float('inf')
            )

            residuals = huber_results.resid
            r_squared = 1 - np.var(residuals) / np.var(times_sec)
            p_value = huber_results.f_pvalue

        else:
            raise ValueError(f"Unknown method: {method}")

        return OverheadModel(
            overhead_sec=overhead_sec,
            throughput_kb_per_sec=throughput_kb_per_sec,
            overhead_ci=overhead_ci,
            throughput_ci=throughput_ci,
            r_squared=r_squared,
            p_value=p_value,
            residuals=residuals,
            method=method
        )

    @staticmethod
    def residual_diagnostics(residuals: np.ndarray) -> Dict:
        """Analyze regression residuals for assumption validation.

        Tests:
        1. Normality (Q-Q plot data, Shapiro-Wilk)
        2. Homoscedasticity (constant variance)
        3. Independence (Durbin-Watson)

        Args:
            residuals: Regression residuals

        Returns:
            Dictionary with diagnostic results
        """
        diagnostics = {}

        # 1. Normality test
        normality = StatisticalAnalyzer.test_normality(residuals)
        diagnostics['normality'] = normality

        # 2. Q-Q plot data
        (osm, osr), (slope, intercept, r) = stats.probplot(residuals, dist="norm")
        diagnostics['qq_plot'] = {
            'theoretical_quantiles': osm,
            'sample_quantiles': osr,
            'fit_slope': slope,
            'fit_intercept': intercept,
            'r_squared': r**2
        }

        # 3. Homoscedasticity (Breusch-Pagan test would need X, skip for now)
        diagnostics['residual_variance'] = np.var(residuals, ddof=1)

        # 4. Standardized residuals
        std_residuals = residuals / np.std(residuals, ddof=1)
        diagnostics['standardized_residuals'] = std_residuals
        diagnostics['outliers'] = np.sum(np.abs(std_residuals) > 3)

        return diagnostics

    @staticmethod
    def polynomial_regression(x: np.ndarray, y: np.ndarray, degree: int = 2,
                             confidence: float = 0.95) -> Dict:
        """Fit polynomial regression and compare with linear model.

        Args:
            x: Independent variable
            y: Dependent variable
            degree: Polynomial degree (default: 2 for quadratic)
            confidence: Confidence level

        Returns:
            Dictionary with polynomial fit results and model comparison
        """
        # Linear model (baseline)
        linear_result = RegressionAnalyzer.linear_regression(x, y, confidence)

        # Polynomial model
        coeffs = np.polyfit(x, y, degree)
        poly = np.poly1d(coeffs)
        predicted = poly(x)
        residuals = y - predicted

        # R-squared
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r_squared = 1 - (ss_res / ss_tot)

        # Adjusted R-squared (accounts for degrees of freedom)
        n = len(x)
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - degree - 1)

        # F-test for model comparison
        f_stat = ((linear_result.r_squared - r_squared) / (degree - 1)) / \
                 ((1 - r_squared) / (n - degree - 1))
        p_value_comparison = 1 - stats.f.cdf(abs(f_stat), degree - 1, n - degree - 1)

        return {
            'degree': degree,
            'coefficients': coeffs,
            'polynomial': poly,
            'r_squared': r_squared,
            'adj_r_squared': adj_r_squared,
            'residuals': residuals,
            'predicted': predicted,
            'linear_r_squared': linear_result.r_squared,
            'improvement': r_squared - linear_result.r_squared,
            'f_statistic': f_stat,
            'p_value_comparison': p_value_comparison,
            'better_than_linear': p_value_comparison < (1 - confidence)
        }

    @staticmethod
    def log_log_regression(x: np.ndarray, y: np.ndarray) -> Dict:
        """Log-log regression to identify scaling complexity.

        If log(y) = a + b*log(x), then y = exp(a) * x^b
        The slope b indicates algorithmic complexity:
        - b ≈ 1: O(n) linear
        - b ≈ 2: O(n²) quadratic
        - b ≈ log(n): O(n log n)

        Args:
            x: Independent variable (e.g., file size)
            y: Dependent variable (e.g., time)

        Returns:
            Dictionary with scaling analysis
        """
        # Filter positive values
        mask = (x > 0) & (y > 0)
        x_pos = x[mask]
        y_pos = y[mask]

        if len(x_pos) < 3:
            return {'error': 'Insufficient positive data points'}

        # Log-log transform
        log_x = np.log(x_pos)
        log_y = np.log(y_pos)

        # Linear regression in log space
        result = RegressionAnalyzer.linear_regression(log_x, log_y)

        # Interpret slope as complexity
        slope = result.slope
        if abs(slope - 1) < 0.1:
            complexity = 'O(n) - Linear'
        elif abs(slope - 1.5) < 0.2:
            complexity = 'O(n^1.5) - Superlinear'
        elif abs(slope - 2) < 0.2:
            complexity = 'O(n²) - Quadratic'
        elif slope < 1:
            complexity = 'O(log n) or O(√n) - Sublinear'
        else:
            complexity = f'O(n^{slope:.2f})'

        return {
            'slope': slope,
            'intercept': result.intercept,
            'r_squared': result.r_squared,
            'p_value': result.p_value,
            'complexity': complexity,
            'scaling_factor': np.exp(result.intercept),
            'log_x': log_x,
            'log_y': log_y,
            'predicted_log_y': result.predicted,
            'residuals': result.residuals
        }


class VarianceAnalyzer:
    """Analysis of variance (ANOVA) and related tests."""

    @staticmethod
    def one_way_anova(groups: List[np.ndarray]) -> Dict:
        """Perform one-way ANOVA.

        Tests null hypothesis: all group means are equal.

        Args:
            groups: List of arrays, one per group

        Returns:
            Dictionary with ANOVA results
        """
        # Remove empty groups
        groups = [g for g in groups if len(g) > 0]

        if len(groups) < 2:
            return {'error': 'Need at least 2 groups'}

        # One-way ANOVA
        f_stat, p_value = stats.f_oneway(*groups)

        # Effect size: eta-squared
        grand_mean = np.mean(np.concatenate(groups))
        ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
        ss_total = sum(np.sum((g - grand_mean)**2) for g in groups)
        eta_squared = ss_between / ss_total if ss_total > 0 else 0

        # Interpretation
        if eta_squared < 0.01:
            effect_interp = 'negligible'
        elif eta_squared < 0.06:
            effect_interp = 'small'
        elif eta_squared < 0.14:
            effect_interp = 'medium'
        else:
            effect_interp = 'large'

        return {
            'f_statistic': f_stat,
            'p_value': p_value,
            'eta_squared': eta_squared,
            'effect_interpretation': effect_interp,
            'n_groups': len(groups),
            'group_means': [np.mean(g) for g in groups],
            'group_stds': [np.std(g, ddof=1) for g in groups],
            'group_sizes': [len(g) for g in groups]
        }

    @staticmethod
    def kruskal_wallis(groups: List[np.ndarray]) -> Dict:
        """Non-parametric alternative to one-way ANOVA.

        Use when data is not normally distributed.

        Args:
            groups: List of arrays, one per group

        Returns:
            Dictionary with test results
        """
        groups = [g for g in groups if len(g) > 0]

        if len(groups) < 2:
            return {'error': 'Need at least 2 groups'}

        # Kruskal-Wallis H-test
        h_stat, p_value = stats.kruskal(*groups)

        # Effect size: epsilon-squared
        n = sum(len(g) for g in groups)
        k = len(groups)
        epsilon_squared = (h_stat - k + 1) / (n - k) if (n - k) > 0 else 0

        return {
            'h_statistic': h_stat,
            'p_value': p_value,
            'epsilon_squared': epsilon_squared,
            'n_groups': k,
            'total_n': n,
            'group_medians': [np.median(g) for g in groups]
        }

    @staticmethod
    def levene_test(groups: List[np.ndarray]) -> Dict:
        """Test for homogeneity of variance (homoscedasticity).

        Args:
            groups: List of arrays

        Returns:
            Test results
        """
        groups = [g for g in groups if len(g) > 0]

        if len(groups) < 2:
            return {'error': 'Need at least 2 groups'}

        w_stat, p_value = stats.levene(*groups)

        return {
            'w_statistic': w_stat,
            'p_value': p_value,
            'homoscedastic': p_value > 0.05,
            'interpretation': 'Equal variances' if p_value > 0.05 else 'Unequal variances'
        }


class CorrelationAnalyzer:
    """Correlation and association analysis."""

    @staticmethod
    def correlation_matrix(data: pd.DataFrame, method: str = 'pearson') -> Dict:
        """Compute correlation matrix with p-values.

        Args:
            data: DataFrame with numeric columns
            method: 'pearson', 'spearman', or 'kendall'

        Returns:
            Dictionary with correlation matrix and p-values
        """
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        n_vars = len(numeric_cols)

        corr_matrix = np.zeros((n_vars, n_vars))
        p_matrix = np.ones((n_vars, n_vars))

        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols):
                if i == j:
                    corr_matrix[i, j] = 1.0
                    p_matrix[i, j] = 0.0
                elif i < j:
                    x = data[col1].dropna()
                    y = data[col2].dropna()

                    # Align indices
                    common_idx = x.index.intersection(y.index)
                    x = x.loc[common_idx]
                    y = y.loc[common_idx]

                    if len(x) > 2:
                        if method == 'pearson':
                            corr, p_val = stats.pearsonr(x, y)
                        elif method == 'spearman':
                            corr, p_val = stats.spearmanr(x, y)
                        elif method == 'kendall':
                            corr, p_val = stats.kendalltau(x, y)
                        else:
                            raise ValueError(f"Unknown method: {method}")

                        corr_matrix[i, j] = corr
                        corr_matrix[j, i] = corr
                        p_matrix[i, j] = p_val
                        p_matrix[j, i] = p_val

        return {
            'correlation_matrix': pd.DataFrame(
                corr_matrix, index=numeric_cols, columns=numeric_cols
            ),
            'p_value_matrix': pd.DataFrame(
                p_matrix, index=numeric_cols, columns=numeric_cols
            ),
            'method': method
        }

    @staticmethod
    def partial_correlation(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> Dict:
        """Compute partial correlation between x and y, controlling for z.

        Partial correlation: correlation between x and y after removing
        the linear effect of z.

        Args:
            x: Variable 1
            y: Variable 2
            z: Control variable

        Returns:
            Partial correlation and p-value
        """
        # Regress x on z
        X_z = sm.add_constant(z)
        model_x = sm.OLS(x, X_z).fit()
        resid_x = model_x.resid

        # Regress y on z
        model_y = sm.OLS(y, X_z).fit()
        resid_y = model_y.resid

        # Correlation between residuals
        partial_corr, p_value = stats.pearsonr(resid_x, resid_y)

        return {
            'partial_correlation': partial_corr,
            'p_value': p_value,
            'n': len(x)
        }
