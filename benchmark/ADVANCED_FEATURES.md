# 📈 Advanced Statistical Features - Complete Guide

## Overview

Extensão completa do sistema de visualização científica com análises estatísticas avançadas para papers de alto impacto. Esta atualização adiciona 5 novas visualizações e 10+ métodos estatísticos.

**Versão:** 3.1.0
**Nova desde:** 3.0.0 → 3.1.0

---

## 🆕 Novas Funcionalidades

### 1. **Análise de Escalabilidade e Complexidade**

#### O Que É?
Identifica a complexidade algorítmica (O(n), O(n²), etc.) através de regressão log-log.

#### Por Que Importa?
- Prediz performance em arquivos maiores
- Identifica gargalos de escalabilidade
- Essencial para otimização de algoritmos

#### Métodos Estatísticos:
```python
from visualization.statistics import RegressionAnalyzer

# Log-log regression
result = RegressionAnalyzer.log_log_regression(file_sizes, execution_times)

print(f"Complexity: {result['complexity']}")  # e.g., "O(n²) - Quadratic"
print(f"Scaling exponent: {result['slope']:.2f}")
print(f"R² = {result['r_squared']:.3f}")
```

**Interpretação do Slope:**
- `slope ≈ 1.0` → **O(n)** Linear (ideal)
- `slope ≈ 1.5` → **O(n^1.5)** Superlinear
- `slope ≈ 2.0` → **O(n²)** Quadratic (problema!)
- `slope < 1.0` → **O(log n)** ou **O(√n)** Sublinear (excelente!)

#### Visualização:
```python
factory.scalability.create_scaling_analysis(data, 'version_strategy', 'output/scaling')
```

**Gera:**
- **(A) Linear Scale**: Scatter plot normal (tempo vs tamanho)
- **(B) Log-Log Scale**: Com linhas de fit e detecção de complexidade
- **(C) Complexity Comparison**: Slopes com referências O(n), O(n²)
- **(D) Throughput Stability**: Throughput deve ser constante se linear

---

### 2. **Comparação de Modelos Polinomiais**

#### O Que É?
Compara fit linear vs. quadrático para determinar se a relação é não-linear.

#### Por Que Importa?
- Modelo linear assume crescimento proporcional
- Se quadrático é melhor, há sobrecarga não-linear (e.g., memória fragmentada)

#### Métodos Estatísticos:
```python
# Fit polynomial e comparar com linear
poly_result = RegressionAnalyzer.polynomial_regression(x, y, degree=2)

print(f"Linear R² = {poly_result['linear_r_squared']:.3f}")
print(f"Quadratic R² = {poly_result['r_squared']:.3f}")
print(f"Improvement = {poly_result['improvement']:.4f}")
print(f"Better than linear? {poly_result['better_than_linear']}")  # F-test p < 0.05
```

**F-test para Comparação de Modelos:**
- H₀: Modelo linear é suficiente
- H₁: Modelo quadrático é significativamente melhor
- Se `p < 0.05`, rejeita H₀ → use quadrático

#### Visualização:
```python
factory.scalability.create_polynomial_comparison(data, 'version_strategy', 'output/poly')
```

**Gera:** 6 painéis (um por estratégia) mostrando:
- Scatter plot dos dados
- Linha de fit linear (azul tracejada)
- Linha de fit quadrática (vermelha sólida)
- R² de cada modelo
- Anotação se quadrático é significativamente melhor

---

### 3. **Análise de Correlação**

#### O Que É?
Matriz de correlação entre TODAS as métricas (tempo, CPU, memória, I/O, etc.) com testes de significância.

#### Por Que Importa?
- Identifica relações entre métricas
- Ajuda a entender bottlenecks (e.g., tempo correlaciona com I/O wait?)
- Detecta multicolinearidade (importante para modelos de ML)

#### Métodos Estatísticos:
```python
from visualization.statistics import CorrelationAnalyzer

analyzer = CorrelationAnalyzer()
result = analyzer.correlation_matrix(data, method='spearman')

corr_matrix = result['correlation_matrix']
p_values = result['p_value_matrix']

# Exemplo: correlação entre tempo e memória
time_memory_corr = corr_matrix.loc['wall_clock_time_sec', 'peak_memory_mb']
p_val = p_values.loc['wall_clock_time_sec', 'peak_memory_mb']
print(f"Correlation: {time_memory_corr:.3f}, p={p_val:.4f}")
```

**Métodos Disponíveis:**
- **Pearson** (r): Linear correlation, assume normalidade
- **Spearman** (ρ): Rank correlation, não-paramétrico (recomendado)
- **Kendall** (τ): Outra opção não-paramétrica, mais conservador

**Correlação Parcial:**
```python
# Correlação entre X e Y, controlando por Z
result = analyzer.partial_correlation(x, y, z)
# Remove efeito linear de Z antes de calcular correlação
```

#### Visualização:
```python
factory.correlation.create_correlation_heatmap(data, 'output/corr', method='spearman')
```

**Gera:**
- **(A) Correlation Matrix**: Heatmap com valores de correlação (-1 a +1)
  - Azul = correlação negativa
  - Vermelho = correlação positiva
  - Estrelas indicam significância (*, **, ***)
- **(B) Significance Map**: -log10(p-value)
  - Quanto maior o valor, mais significativo
  - Linhas de referência em p=0.05 e p=0.01

---

### 4. **Análise de Variância (ANOVA)**

#### O Que É?
Testa se as médias de múltiplos grupos são diferentes. Versão multi-grupo do t-test.

#### Por Que Importa?
- Resposta científica para "qual estratégia é melhor?"
- ANOVA paramétrico (assume normalidade)
- Kruskal-Wallis não-paramétrico (alternativa robusta)

#### Métodos Estatísticos:

**ANOVA (Paramétrico):**
```python
from visualization.statistics import VarianceAnalyzer

analyzer = VarianceAnalyzer()

# One-way ANOVA
groups = [data1, data2, data3]  # List of arrays
result = analyzer.one_way_anova(groups)

print(f"F-statistic: {result['f_statistic']:.4f}")
print(f"p-value: {result['p_value']:.4e}")
print(f"η² (eta-squared): {result['eta_squared']:.4f}")  # Effect size
print(f"Interpretation: {result['effect_interpretation']}")  # small, medium, large
```

**Kruskal-Wallis (Não-Paramétrico):**
```python
# Use quando dados não são normais
kw_result = analyzer.kruskal_wallis(groups)

print(f"H-statistic: {kw_result['h_statistic']:.4f}")
print(f"p-value: {kw_result['p_value']:.4e}")
print(f"ε² (epsilon-squared): {kw_result['epsilon_squared']:.4f}")
```

**Levene's Test (Homoscedasticidade):**
```python
# Testa se variâncias são iguais (assumção do ANOVA)
levene_result = analyzer.levene_test(groups)

if levene_result['homoscedastic']:
    print("✓ Use ANOVA (variâncias iguais)")
else:
    print("✗ Use Welch's ANOVA ou Kruskal-Wallis (variâncias desiguais)")
```

#### Visualização:
```python
factory.variance.create_anova_summary(data, 'version_strategy', 'output/anova')
```

**Gera:**
- **(A) Box Plot**: Com notches (intervalos de confiança) e médias (diamante vermelho)
- **(B) ANOVA Results**:
  - F-statistic, p-value, η²
  - Resultado do Levene's test
  - Interpretação de assumções
- **(C) Kruskal-Wallis Results**:
  - H-statistic, p-value, ε²
  - Recomendação quando usar

---

### 5. **Comparação de Modelos de Regressão**

#### O Que É?
Compara diferentes modelos de regressão para encontrar o melhor fit.

#### Modelos Disponíveis:

**Linear (OLS):**
```python
result = RegressionAnalyzer.linear_regression(x, y, confidence=0.95)
# time = intercept + slope * size
```

**Robust (Huber):**
```python
model = RegressionAnalyzer.overhead_model(sizes, times, method='robust')
# Menos sensível a outliers
```

**Polynomial:**
```python
poly_result = RegressionAnalyzer.polynomial_regression(x, y, degree=2)
# time = a + b*size + c*size²
```

**Log-Log:**
```python
log_result = RegressionAnalyzer.log_log_regression(x, y)
# log(time) = a + b*log(size) → time = exp(a) * size^b
```

#### Diagnósticos de Regressão:
```python
diagnostics = RegressionAnalyzer.residual_diagnostics(residuals)

# Normalidade dos resíduos
print(f"Normal? {diagnostics['normality']['is_normal']}")

# Q-Q plot data
qq_data = diagnostics['qq_plot']

# Outliers (|z| > 3)
print(f"Outliers detected: {diagnostics['outliers']}")
```

---

## 📊 Sumário das Análises Estatísticas

| Análise | Método | Quando Usar | Output |
|---------|--------|-------------|--------|
| **Effect Size** | Cohen's d, Hedges' g | Após encontrar p < 0.05 | Magnitude: small/medium/large |
| **Multiple Comparisons** | FDR (Benjamini-Hochberg) | Múltiplos testes simultâneos | p-values corrigidos |
| **Normality** | Shapiro-Wilk, D'Agostino | Antes de testes paramétricos | is_normal: True/False |
| **Regression** | OLS, Huber, Polynomial | Modelar relação X → Y | Slope, R², CI, diagnostics |
| **Complexity** | Log-log regression | Identificar O(n), O(n²) | Scaling exponent |
| **Correlation** | Pearson, Spearman | Associação entre métricas | Correlation matrix + p-values |
| **ANOVA** | F-test, Kruskal-Wallis | Comparar 3+ grupos | F/H-statistic, η²/ε² |
| **Homoscedasticity** | Levene's test | Validar ANOVA | Equal variances: Yes/No |

---

## 🔬 Fluxo de Análise Recomendado

### Para Papers Científicos:

#### Etapa 1: Exploração de Dados
1. **Distribution Analysis** (Visualization #6)
   - Violin + KDE + ECDF
   - Identifica outliers, multimodalidade

2. **Normality Tests** (Visualization #4)
   - Q-Q plots
   - Decide: paramétrico vs não-paramétrico

3. **Correlation Heatmap** (Visualization #10)
   - Identifica relações entre métricas
   - Detecta multicolinearidade

#### Etapa 2: Comparações Entre Grupos
4. **Normalized Performance** (Visualization #1)
   - Comparação justa (time per MB)

5. **Effect Size Comparison** (Visualization #2)
   - Magnitude das diferenças (Cohen's d)

6. **Pairwise Significance** (Visualization #5)
   - Testes com FDR correction

7. **ANOVA Summary** (Visualization #11)
   - Teste omnibus (todas as estratégias)
   - Kruskal-Wallis se não-normal

#### Etapa 3: Modelagem
8. **Overhead Decomposition** (Visualization #3)
   - Separa overhead fixo vs. processamento

9. **Scaling Analysis** (Visualization #8)
   - Log-log para identificar complexidade
   - Prediz performance em arquivos maiores

10. **Polynomial Comparison** (Visualization #9)
    - Testa se relação é não-linear

#### Etapa 4: Recursos
11. **Resource Efficiency** (Visualization #7)
    - Memory, CPU, I/O analysis

---

## 💡 Exemplos Práticos

### Exemplo 1: Identificar Complexidade

```python
from visualization import VisualizationConfig, ChartFactory
import pandas as pd

# Load data
data = pd.read_csv('benchmark_results.csv')

# Setup
config = VisualizationConfig(mode='paper')
config.apply()
factory = ChartFactory(config)

# Generate scaling analysis
factory.scalability.create_scaling_analysis(
    data, 'version_strategy', 'analysis/scaling'
)

# The log-log plot will show slopes:
# - Strategy A: slope = 1.02 → O(n) - Linear ✓
# - Strategy B: slope = 1.98 → O(n²) - Quadratic ✗ (needs optimization!)
```

### Exemplo 2: Testar Se Diferenças São Significativas

```python
from visualization.statistics import VarianceAnalyzer

# Prepare groups
analyzer = VarianceAnalyzer()
groups = [
    data[data['strategy'] == 'presidio']['wall_clock_time_sec'].values,
    data[data['strategy'] == 'filtered']['wall_clock_time_sec'].values,
    data[data['strategy'] == 'hybrid']['wall_clock_time_sec'].values,
]

# Test normality first
from visualization.statistics import StatisticalAnalyzer
stat_analyzer = StatisticalAnalyzer()
for i, group in enumerate(groups):
    result = stat_analyzer.test_normality(group)
    print(f"Group {i}: {'Normal' if result['is_normal'] else 'Non-normal'}")

# If normal: ANOVA
anova_result = analyzer.one_way_anova(groups)
print(f"ANOVA p-value: {anova_result['p_value']:.4e}")
print(f"Effect size (η²): {anova_result['eta_squared']:.4f}")

# If non-normal: Kruskal-Wallis
kw_result = analyzer.kruskal_wallis(groups)
print(f"Kruskal-Wallis p-value: {kw_result['p_value']:.4e}")

# Conclusion:
if anova_result['p_value'] < 0.05:
    print("✓ Strategies have significantly different performance")
    print(f"  Effect: {anova_result['effect_interpretation']}")
else:
    print("✗ No significant difference between strategies")
```

### Exemplo 3: Encontrar Métricas Correlacionadas

```python
from visualization.statistics import CorrelationAnalyzer

analyzer = CorrelationAnalyzer()
result = analyzer.correlation_matrix(data, method='spearman')

corr_matrix = result['correlation_matrix']

# Find strongest correlations
# Flatten upper triangle
corr_flat = []
n = len(corr_matrix)
for i in range(n):
    for j in range(i+1, n):
        corr_flat.append({
            'var1': corr_matrix.index[i],
            'var2': corr_matrix.columns[j],
            'correlation': corr_matrix.iloc[i, j],
            'p_value': result['p_value_matrix'].iloc[i, j]
        })

# Sort by absolute correlation
import pandas as pd
corr_df = pd.DataFrame(corr_flat)
corr_df['abs_corr'] = corr_df['correlation'].abs()
top_corr = corr_df.nlargest(5, 'abs_corr')

print("Top 5 Correlations:")
print(top_corr[['var1', 'var2', 'correlation', 'p_value']])

# Example output:
# var1                    var2                    correlation  p_value
# wall_clock_time_sec     file_size_mb            0.92        < 0.001
# io_wait_percent         wall_clock_time_sec     0.85        < 0.001
# cpu_percent             throughput_mb_per_sec   -0.78       < 0.001
```

---

## 📚 Referências Científicas

### Métodos Estatísticos
1. **ANOVA**: Fisher, R. A. (1925). *Statistical Methods for Research Workers*
2. **Kruskal-Wallis**: Kruskal & Wallis (1952). *JASA*
3. **Spearman Correlation**: Spearman, C. (1904). *American Journal of Psychology*
4. **Levene's Test**: Levene, H. (1960). *Contributions to Probability and Statistics*
5. **Polynomial Regression**: Draper & Smith (1998). *Applied Regression Analysis*

### Complexity Analysis
6. **Big-O Notation**: Knuth, D. E. (1976). *The Art of Computer Programming*
7. **Empirical Complexity**: Goldsmith, J. et al. (2007). *Empirical Algorithms*

### Effect Sizes
8. **Eta-Squared**: Cohen, J. (1973). *Psychological Bulletin*
9. **Epsilon-Squared**: Tomczak & Tomczak (2014). *Trends in Sport Sciences*

---

## 🎯 Checklist para Papers

Antes de submeter, verifique que você tem:

### Análise de Dados
- [ ] Estatísticas descritivas (média, mediana, DP)
- [ ] Testes de normalidade executados e reportados
- [ ] Effect sizes calculados (não apenas p-values)
- [ ] Correção para comparações múltiplas aplicada
- [ ] Análise de complexidade (log-log) realizada
- [ ] Modelos de regressão com diagnósticos

### Visualizações
- [ ] Normalized metrics (não raw time by format)
- [ ] Correlation heatmap com significância
- [ ] Distribution plots (violin/KDE/ECDF)
- [ ] Q-Q plots para normalidade
- [ ] Log-log plots para complexidade
- [ ] Box plots com médias e CIs

### Relatório
- [ ] Método estatístico justificado (paramétrico vs não-paramétrico)
- [ ] Assumções validadas (normalidade, homoscedasticidade)
- [ ] Sample sizes reportados
- [ ] Todos os testes com correção FDR
- [ ] Effect sizes interpretados (small/medium/large)
- [ ] Complexity identificada (O(n), O(n²), etc.)

---

## 🚀 Próximos Passos

1. **Rode análise completa:**
   ```bash
   python benchmark/analyze_benchmark_scientific.py results.csv
   ```

2. **Revise as 12 visualizações** em `benchmark/results/scientific/`

3. **Leia o relatório estatístico** (`statistical_report.txt`)

4. **Selecione 6-8 figuras** para seu paper:
   - Normalized Performance (obrigatório)
   - Effect Size Forest Plot (obrigatório)
   - Overhead Decomposition (recomendado)
   - Scaling Analysis (se relevante para conclusões)
   - Correlation Heatmap (se discute métricas relacionadas)
   - ANOVA Summary (se compara 3+ estratégias)
   - Distribution Analysis (se discute variabilidade)
   - Q-Q Plots (em apêndice para validar assumções)

5. **Escreva seção de Resultados** baseada nas análises

6. **Valide assumções** antes de reportar testes paramétricos

---

**Versão:** 3.1.0
**Atualizado:** 2026-02-08
**Autores:** AnonShield Team
