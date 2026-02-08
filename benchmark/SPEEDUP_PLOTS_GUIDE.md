# 🚀 Speedup Plots - Quick Guide

## Overview

Gráficos de speedup são **essenciais** para papers mostrando melhorias de performance. Agora temos suporte completo para gerar esses gráficos automaticamente!

---

## ✅ Sim! Temos Gráficos Iguais ao Seu Exemplo

### O Que Você Mostrou:
```python
# Seu código tinha:
# 1. Tempo vs Tamanho (log scale)
# 2. Throughput vs Tamanho
# 3. Anotações de speedup
# 4. Múltiplas versões/estratégias
```

### O Que Criamos:
```python
# Agora temos visualização #13:
factory.scalability.create_speedup_comparison(data, baseline, output)

# Gera automaticamente:
# Panel A: Time vs Size (log-log scale) com speedup annotations
# Panel B: Throughput vs Size com indicadores de estabilidade
# Estilo publication-ready (300 DPI, colorblind-safe)
```

---

## 🎯 3 Formas de Usar

### 1. **Análise Completa Automática** (Mais Fácil)
```bash
python benchmark/analyze_benchmark_scientific.py results.csv
```

**Gera:**
- `13_speedup_comparison.png/pdf` ← Novo gráfico!
- Mais 12 outras visualizações

---

### 2. **Gráfico Individual**
```python
from visualization import VisualizationConfig, ChartFactory
import pandas as pd

# Load data
df = pd.read_csv('results.csv')

# Setup
config = VisualizationConfig(mode='paper')
factory = ChartFactory(config)

# Generate ONLY speedup plot
factory.scalability.create_speedup_comparison(
    df,
    baseline_strategy='v2.0_default',  # Reference strategy
    output_path='output/speedup'
)

# Output: speedup.png + speedup.pdf (300 DPI)
```

---

### 3. **Com Seus Dados Customizados**
```python
# Converta seus dados para o formato esperado
import numpy as np
import pandas as pd

# Seus dados
data_dict = {
    'Size_MB': [0.25, 0.50, 1.00, 2.00],
    'v2.0_Time': [211.55, 440.43, 871.07, 1908.79],
    'v3.0_Standalone_Time': [10.64, 14.53, 21.76, 32.05],
    'v3.0_Hybrid_Time': [18.89, 26.76, 41.81, np.nan]
}

# Converta para DataFrame benchmark
rows = []
for i, size in enumerate(data_dict['Size_MB']):
    for strategy, times_key in [
        ('v2.0_default', 'v2.0_Time'),
        ('v3.0_standalone', 'v3.0_Standalone_Time'),
        ('v3.0_hybrid', 'v3.0_Hybrid_Time')
    ]:
        time = data_dict[times_key][i]
        if not np.isnan(time):
            rows.append({
                'version_strategy': strategy,
                'file_size_mb': size,
                'wall_clock_time_sec': time,
                'throughput_mb_per_sec': size / time,
                # Adicione outros campos se disponíveis
            })

df = pd.DataFrame(rows)

# Gere o gráfico
from visualization import VisualizationConfig, ChartFactory

config = VisualizationConfig(mode='paper')
factory = ChartFactory(config)

factory.scalability.create_speedup_comparison(
    df, 'v2.0_default', 'output/speedup'
)
```

---

## 📊 Exemplo Completo Funcional

Criamos um script pronto para usar:

```bash
python benchmark/example_speedup_plot.py
```

**O que ele faz:**
1. Usa seus dados exatos (do código que você mostrou)
2. Converte para formato benchmark
3. Gera gráfico speedup automaticamente
4. Salva em `benchmark/results/speedup_example/`

---

## 🎨 Diferenças vs Seu Código Original

| Aspecto | Seu Código | Nossa Framework |
|---------|-----------|-----------------|
| **Estilo** | Manual (`seaborn-v0_8-whitegrid`) | Auto (colorblind-safe Wong palette) |
| **DPI** | Não especificado (default ~100) | 300 DPI (print-ready) |
| **Formatos** | PNG apenas | PNG + PDF vetorial |
| **Tamanhos** | Arbitrário (16x7) | IEEE standard (7.0 × 4.0") |
| **Speedup Annotations** | Manual | **Automático** |
| **Log Scale** | Manual (ambos eixos) | **Automático** (detecta melhor escala) |
| **Stability Indicators** | Não tem | **Tem** (CV no throughput) |
| **Cores** | Default matplotlib | **Colorblind-safe** |

---

## 📈 O Que o Gráfico Mostra

### Panel A: Time vs Size (Log-Log)
- **Eixo X**: File Size (MB) - log scale
- **Eixo Y**: Execution Time (sec) - log scale
- **Linhas**: Uma por estratégia
  - Baseline: tracejada
  - Outras: sólidas
- **Anotações**: Speedup automático no tamanho mediano
  - Exemplo: "20.8×" indica 20.8 vezes mais rápido que baseline

**Interpretação:**
- Linhas paralelas → mesma complexidade algorítmica
- Distância vertical → diferença de performance constante
- Slope ≈ 1 → O(n) linear
- Slope ≈ 2 → O(n²) quadratic

### Panel B: Throughput vs Size
- **Eixo X**: File Size (MB) - log scale
- **Eixo Y**: Throughput (MB/sec) - linear scale
- **Linhas**: Uma por estratégia
- **Anotações**: "Stable (CV=0.15)" indica throughput constante

**Interpretação:**
- Linha horizontal → throughput constante → escalabilidade perfeita (O(n))
- Linha decrescente → throughput cai com arquivos maiores → problema de escalabilidade
- CV < 0.2 → estável, CV > 0.5 → instável

---

## 🔢 Cálculos Automáticos

O sistema calcula automaticamente:

1. **Speedup**:
   ```
   speedup = baseline_time / strategy_time
   ```
   - Speedup > 1: mais rápido que baseline
   - Speedup < 1: mais lento que baseline

2. **Throughput**:
   ```
   throughput = file_size_mb / execution_time_sec
   ```

3. **Coefficient of Variation (CV)**:
   ```
   CV = std(throughput) / mean(throughput)
   ```
   - CV < 0.2: estável (bom)
   - CV > 0.5: instável (problema)

4. **Log-Log Slope** (complexidade):
   ```
   log(time) = a + b * log(size)
   slope = b
   ```
   - b ≈ 1: O(n) linear
   - b ≈ 2: O(n²) quadratic

---

## 💡 Dicas para Papers

### Para Conference Papers:
Use **Speedup Comparison** como figura principal:
- Mostra claramente a melhoria
- Duas métricas em um gráfico (tempo + throughput)
- Anotações de speedup chamam atenção

### Para Journal Papers:
Combine com outras figuras:
1. **Speedup Comparison** (overview)
2. **Overhead Decomposition** (detalha onde vem o speedup)
3. **Scaling Analysis** (mostra complexidade)

### Texto Sugerido:
```latex
Figure X shows the speedup comparison between versions.
Panel A demonstrates execution time across file sizes on a
log-log scale, revealing that v3.0 achieves a 20.8× speedup
over v2.0 at 1.00 MB. Panel B shows throughput remains
stable (CV=0.15), indicating O(n) linear scalability.
```

---

## 🚀 Quick Start

**1 comando para tudo:**
```bash
python benchmark/example_speedup_plot.py
```

**Ou integrado na análise completa:**
```bash
python benchmark/analyze_benchmark_scientific.py results.csv
# Gera visualização #13: speedup_comparison.png/pdf
```

---

## 📁 Arquivos Relevantes

```
benchmark/
├── example_speedup_plot.py              # ⭐ NOVO: Exemplo standalone
├── analyze_benchmark_scientific.py      # Atualizado: inclui speedup (#13)
└── visualization/
    └── charts.py                        # Atualizado: create_speedup_comparison()
```

---

## ⚙️ Customização Avançada

Se quiser ajustar o gráfico:

```python
# Acesse configurações
config = VisualizationConfig(mode='paper')

# Mude tamanho da figura
figsize = config.get_figure_size('double_wide')  # (7.0, 4.0)

# Ou customize:
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

# Mude cores
colors = config.get_colors(n=3)  # Wong palette, colorblind-safe

# Mude DPI
config.save_figure(fig, 'output', dpi=600)  # 600 DPI para impressão
```

---

## 🐛 Troubleshooting

### Erro: "No data for baseline strategy"
**Solução:** Certifique que `baseline_strategy` existe nos dados
```python
print(df['version_strategy'].unique())  # Veja estratégias disponíveis
```

### Erro: "Not enough data points"
**Solução:** Precisa de pelo menos 2 tamanhos de arquivo diferentes
```python
print(df.groupby('file_size_mb').size())  # Veja distribuição
```

### Gráfico vazio
**Solução:** Verifique que dados têm `file_size_mb` e `wall_clock_time_sec`
```python
print(df.columns)  # Veja colunas disponíveis
print(df[['file_size_mb', 'wall_clock_time_sec']].head())
```

---

## 📚 Referências

- **Log-Log Plots**: Clauset et al. (2009). *Power-Law Distributions in Empirical Data*
- **Speedup Metrics**: Gustafson's Law (1988). *Reevaluating Amdahl's Law*
- **Scalability Analysis**: Bondi (2000). *Foundations of Software and System Performance*

---

**Criado:** 2026-02-08
**Versão:** 3.1.0
**Status:** ✅ Production Ready
