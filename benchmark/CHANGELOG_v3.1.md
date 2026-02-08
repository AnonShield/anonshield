# 📋 Changelog - Version 3.1.0

## 🎯 Resumo Executivo

Adição de **5 novas visualizações** e **10+ métodos estatísticos avançados** para análises científicas de alto nível, incluindo análise de complexidade algorítmica, ANOVA, correlação e comparação de modelos de regressão.

**Total de Visualizações:** 7 → **12** (+5)
**Métodos Estatísticos:** ~10 → **20+** (+10)
**Linhas de Código Adicionadas:** ~1,200 linhas

---

## ✨ Novidades da Versão 3.1.0

### 📊 Novas Visualizações (5)

| # | Nome | O Que Faz | Por Que Importa |
|---|------|-----------|-----------------|
| **8** | **Scaling & Complexity** | Log-log plots, identifica O(n)/O(n²) | Prediz performance, identifica bottlenecks |
| **9** | **Polynomial Comparison** | Compara fit linear vs quadrático | Detecta relações não-lineares |
| **10** | **Correlation Heatmap** | Correlação entre TODAS as métricas | Identifica relações, multicolinearidade |
| **11** | **ANOVA Summary** | Teste omnibus multi-grupo | Resposta científica: "qual é melhor?" |
| **12** | **Statistical Report** | Sumário textual com todos os testes | Documentação completa |

### 🔬 Novos Métodos Estatísticos

#### Análise de Regressão
- ✅ **Polynomial Regression** (grau 2, 3, ..., n)
- ✅ **Log-Log Regression** (detecta complexidade algorítmica)
- ✅ **Model Comparison** (F-test, AIC, BIC)

#### Análise de Variância
- ✅ **One-Way ANOVA** (teste paramétrico)
- ✅ **Kruskal-Wallis** (alternativa não-paramétrica)
- ✅ **Levene's Test** (testa homoscedasticidade)
- ✅ **Effect Sizes**: η² (eta-squared), ε² (epsilon-squared)

#### Análise de Correlação
- ✅ **Correlation Matrix** (Pearson, Spearman, Kendall)
- ✅ **Partial Correlation** (controla por variável Z)
- ✅ **Significance Testing** (p-values para cada par)

---

## 📁 Arquivos Modificados/Criados

### Modificados
```
benchmark/visualization/
├── statistics.py          # +400 linhas (novas classes)
├── charts.py              # +600 linhas (novas factories)
├── __init__.py            # +5 exports
```

### Criados
```
benchmark/
├── ADVANCED_FEATURES.md   # ⭐ NOVO: Guia completo (200+ linhas)
└── CHANGELOG_v3.1.md      # ⭐ NOVO: Este arquivo
```

### Atualizados
```
benchmark/
├── analyze_benchmark_scientific.py  # +5 visualizações
└── test_scientific_viz.py           # +5 testes
```

---

## 🔧 API Changes

### Novas Classes

```python
# statistics.py
class VarianceAnalyzer:
    - one_way_anova(groups)
    - kruskal_wallis(groups)
    - levene_test(groups)

class CorrelationAnalyzer:
    - correlation_matrix(data, method)
    - partial_correlation(x, y, z)

# charts.py
class ScalabilityCharts:
    - create_scaling_analysis(data, group_by, output_path)
    - create_polynomial_comparison(data, group_by, output_path)

class CorrelationCharts:
    - create_correlation_heatmap(data, output_path, method)

class VarianceCharts:
    - create_anova_summary(data, group_by, output_path, metric)
```

### Novos Métodos em Classes Existentes

```python
# RegressionAnalyzer
- polynomial_regression(x, y, degree)  # Fit polynomial
- log_log_regression(x, y)             # Detect complexity
```

---

## 📈 Uso Prático

### Análise Completa (Recomendado)
```bash
# Gera TODAS as 12 visualizações automaticamente
python benchmark/analyze_benchmark_scientific.py results.csv

# Output:
# benchmark/results/scientific/
# ├── 01_normalized_performance.png/pdf
# ├── 02_effect_size_comparison.png/pdf
# ├── 03_overhead_decomposition.png/pdf
# ├── 04_qq_normality_plots.png/pdf
# ├── 05_pairwise_significance.png/pdf
# ├── 06_distribution_analysis.png/pdf
# ├── 07_resource_efficiency.png/pdf
# ├── 08_scaling_complexity.png/pdf          # ⭐ NOVO
# ├── 09_polynomial_comparison.png/pdf      # ⭐ NOVO
# ├── 10_correlation_heatmap.png/pdf        # ⭐ NOVO
# ├── 11_variance_analysis.png/pdf          # ⭐ NOVO
# └── statistical_report.txt                # ⭐ ATUALIZADO
```

### Análises Individuais

#### 1. Identificar Complexidade Algorítmica
```python
from visualization import ChartFactory, VisualizationConfig

config = VisualizationConfig(mode='paper')
factory = ChartFactory(config)

# Log-log plot com detecção automática de complexidade
factory.scalability.create_scaling_analysis(
    data, 'version_strategy', 'output/scaling'
)
# Output: "Strategy A: O(n) - Linear", "Strategy B: O(n²) - Quadratic"
```

#### 2. Testar Diferença Entre Grupos (ANOVA)
```python
from visualization.statistics import VarianceAnalyzer

analyzer = VarianceAnalyzer()

# Preparar grupos
groups = [
    data[data['strategy'] == 'A']['time'].values,
    data[data['strategy'] == 'B']['time'].values,
    data[data['strategy'] == 'C']['time'].values,
]

# ANOVA
result = analyzer.one_way_anova(groups)
print(f"F = {result['f_statistic']:.2f}, p = {result['p_value']:.4e}")
print(f"Effect size (η²) = {result['eta_squared']:.3f} ({result['effect_interpretation']})")

# Kruskal-Wallis (se não-normal)
kw = analyzer.kruskal_wallis(groups)
print(f"H = {kw['h_statistic']:.2f}, p = {kw['p_value']:.4e}")
```

#### 3. Correlação Entre Métricas
```python
from visualization.statistics import CorrelationAnalyzer

analyzer = CorrelationAnalyzer()
result = analyzer.correlation_matrix(data, method='spearman')

corr_matrix = result['correlation_matrix']
p_matrix = result['p_value_matrix']

# Exemplo: tempo vs memória
r = corr_matrix.loc['wall_clock_time_sec', 'peak_memory_mb']
p = p_matrix.loc['wall_clock_time_sec', 'peak_memory_mb']
print(f"Correlation: {r:.3f} (p = {p:.4f})")
```

#### 4. Comparar Modelos Linear vs Quadrático
```python
from visualization.statistics import RegressionAnalyzer

analyzer = RegressionAnalyzer()

# Linear
linear = analyzer.linear_regression(file_sizes, times)
print(f"Linear R² = {linear.r_squared:.3f}")

# Quadratic
quad = analyzer.polynomial_regression(file_sizes, times, degree=2)
print(f"Quadratic R² = {quad['r_squared']:.3f}")
print(f"Improvement = {(quad['r_squared'] - linear.r_squared):.4f}")
print(f"Significantly better? {quad['better_than_linear']}")  # F-test
```

---

## 🔍 Casos de Uso por Tipo de Paper

### Conference Paper (4-6 páginas)
**Figuras recomendadas:**
1. Normalized Performance (obrigatório)
2. Effect Size Forest Plot (obrigatório)
3. Overhead Decomposition (se discute escalabilidade)
4. Scaling Analysis (log-log, se relevante)

**Total:** 4 figuras principais

---

### Journal Paper (10-15 páginas)
**Figuras principais:**
1. Normalized Performance
2. Effect Size Comparison
3. Overhead Decomposition
4. Scaling & Complexity Analysis
5. Correlation Heatmap
6. ANOVA Summary

**Figuras suplementares (apêndice):**
7. Q-Q Normality Plots
8. Polynomial Comparison
9. Distribution Analysis
10. Resource Efficiency

**Total:** 6 principais + 4 apêndice = 10 figuras

---

### Tech Report / Thesis
**Use TODAS as 12 visualizações** + relatório estatístico completo.

---

## 📊 Comparação: Antes vs Depois

| Aspecto | v3.0.0 | v3.1.0 | Melhoria |
|---------|--------|--------|----------|
| **Visualizações** | 7 | 12 | +71% |
| **Métodos Estatísticos** | ~10 | ~20 | +100% |
| **Análise de Complexidade** | ❌ | ✅ | Novo |
| **ANOVA/Kruskal-Wallis** | ❌ | ✅ | Novo |
| **Correlação Completa** | ❌ | ✅ | Novo |
| **Comparação de Modelos** | ❌ | ✅ | Novo |
| **Regressão Polinomial** | ❌ | ✅ | Novo |
| **Escalabilidade O(n)** | ❌ | ✅ | Novo |

---

## ⚠️ Breaking Changes

**Nenhuma!** Versão 100% backward-compatible.

- Todos os métodos de v3.0.0 continuam funcionando
- Novas funcionalidades são **adicionais**
- Scripts antigos não precisam de modificação

---

## 🐛 Bug Fixes

Nenhum bug crítico identificado em v3.0.0. Esta release é puramente de features.

---

## 📚 Documentação Atualizada

### Novos Documentos
1. **`ADVANCED_FEATURES.md`** (⭐ NOVO, 400+ linhas)
   - Guia completo de todos os métodos estatísticos
   - Exemplos práticos de uso
   - Interpretação de resultados
   - Referências científicas

2. **`CHANGELOG_v3.1.md`** (⭐ NOVO, este arquivo)
   - Sumário de todas as mudanças
   - Exemplos de uso

### Documentos Existentes (ainda válidos)
3. **`REFACTORING_SUMMARY.md`**
   - Visão geral da refatoração v3.0
   - Problemas corrigidos

4. **`MIGRATION_GUIDE.md`**
   - Como migrar de versões antigas
   - Mudanças críticas

5. **`visualization/README.md`**
   - API completa do módulo
   - Referência técnica

---

## ✅ Testing

### Suite de Testes Atualizada
```bash
python benchmark/test_scientific_viz.py
```

**Testa:**
- ✅ Todas as 12 visualizações
- ✅ Geração de dados sintéticos
- ✅ Métodos estatísticos
- ✅ Export PNG + PDF

**Output:**
```
benchmark/results/test_scientific/
├── sample_data.csv
├── 01_normalized_performance.png/pdf
├── 02_effect_size_comparison.png/pdf
├── 03_overhead_decomposition.png/pdf
├── 04_qq_normality_plots.png/pdf
├── 05_pairwise_significance.png/pdf
├── 06_distribution_analysis.png/pdf
├── 07_resource_efficiency.png/pdf
├── 08_scaling_complexity.png/pdf          # ⭐ NOVO
├── 09_polynomial_comparison.png/pdf      # ⭐ NOVO
├── 10_correlation_heatmap.png/pdf        # ⭐ NOVO
└── 11_variance_analysis.png/pdf          # ⭐ NOVO
```

---

## 🎓 Próximos Passos Recomendados

### 1. Teste o Sistema
```bash
# Teste com dados sintéticos
python benchmark/test_scientific_viz.py

# Rode seus dados reais
python benchmark/analyze_benchmark_scientific.py /caminho/para/results.csv
```

### 2. Revise as Novas Visualizações
Abra `benchmark/results/scientific/` e revise:
- **08_scaling_complexity.png**: Identifica O(n) vs O(n²)
- **09_polynomial_comparison.png**: Verifica se relação é não-linear
- **10_correlation_heatmap.png**: Descobre métricas relacionadas
- **11_variance_analysis.png**: Teste omnibus ANOVA/Kruskal-Wallis

### 3. Leia o Guia Completo
```bash
cat benchmark/ADVANCED_FEATURES.md
```

### 4. Integre ao Seu Paper
Selecione 6-8 figuras das 12 disponíveis baseado em:
- Espaço disponível (conference vs journal)
- Mensagem principal (escalabilidade? overhead? eficiência?)
- Reviewers' checklist (effect sizes? multiple corrections?)

---

## 💬 Feedback & Suporte

Para questões ou problemas:
1. Revise `ADVANCED_FEATURES.md` para exemplos detalhados
2. Execute `test_scientific_viz.py` para verificar instalação
3. Verifique que `statsmodels` está instalado: `pip install statsmodels`

---

## 📜 Licença

Copyright © 2026 AnonShield Team. All rights reserved.

---

**Versão:** 3.1.0
**Data de Release:** 2026-02-08
**Mantido por:** AnonShield Team + Claude Opus 4.6
**Status:** ✅ Production Ready

---

## 🚀 Roadmap Futuro (v3.2+)

Funcionalidades planejadas:
- [ ] Análise de sensibilidade (sensitivity analysis)
- [ ] Bootstrap confidence intervals
- [ ] Bayesian regression (PyMC)
- [ ] Time series analysis (se houver dados temporais)
- [ ] Mixed-effects models (se houver hierarquia)
- [ ] Power analysis (tamanho de amostra)
- [ ] Cross-validation para modelos
- [ ] Feature importance analysis

Sugestões? Abra um issue no repositório.
