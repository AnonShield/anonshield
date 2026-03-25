# 🚀 Guia de Início Rápido - Dataset Multi-Formato

Guia prático para converter e analisar o dataset em múltiplos formatos.

## ⚡ TL;DR (Execução Rápida)

```bash
# 1. Instalar dependências
pip install openpyxl python-docx pdf2image pillow
sudo apt-get install poppler-utils  # Ubuntu/Debian

# 2. Verificar status
python scripts/check_dataset_status.py

# 3. Executar workflow completo (automático)
./scripts/complete_benchmark_workflow.sh

# Ou manualmente:
# 3a. Converter datasets
python scripts/convert_dataset.py --all

# 3b. Gerar estatísticas
python scripts/analyze_dataset.py --dirs vulnnet_scans_openvas

# 3c. Rodar benchmarks
python benchmark/benchmark.py --benchmark --directory-mode --data-dir vulnnet_scans_openvas --runs 2
```

## 📋 Verificação Pré-voo

### 1. Verificar ambiente

```bash
# Checar se está no ambiente correto
which python
# Deve mostrar: /home/kapelinski/Documents/tool/.venv/bin/python

# Ativar se necessário
source .venv/bin/activate
```

### 2. Verificar dependências

```bash
# Testar imports Python
python -c "import openpyxl, docx, pdf2image; print('✓ All deps OK')"

# Testar poppler
pdftoppm -h > /dev/null && echo "✓ poppler OK" || echo "✗ poppler missing"
```

### 3. Verificar dataset original

```bash
# Ver estrutura
ls vulnnet_scans_openvas | head -10

# Contar arquivos por tipo
find vulnnet_scans_openvas -type f -name "*.csv" | wc -l
find vulnnet_scans_openvas -type f -name "*.xml" | wc -l
find vulnnet_scans_openvas -type f -name "*.pdf" | wc -l
```

### 4. Verificar espaço em disco

```bash
df -h .
# Precisa de pelo menos 500 MB livres (recomendado: 1 GB)
```

## 🎯 Opção 1: Workflow Automático (Recomendado)

### Executar tudo de uma vez

```bash
./scripts/complete_benchmark_workflow.sh
```

Isso irá:
1. ✓ Verificar dependências
2. ✓ Converter para XLSX, DOCX, JSON, Images
3. ✓ Gerar estatísticas completas
4. ✓ Executar benchmarks em todos os formatos
5. ✓ Gerar relatórios consolidados

**Tempo estimado**: 30-60 minutos (dependendo do hardware)

### Customizar execução

```bash
# Mais workers (mais rápido)
WORKERS=16 ./scripts/complete_benchmark_workflow.sh

# Mais runs (mais preciso)
RUNS=3 ./scripts/complete_benchmark_workflow.sh

# Versões específicas
VERSIONS="3.0" ./scripts/complete_benchmark_workflow.sh

# Combinado
WORKERS=16 RUNS=3 VERSIONS="2.0 3.0" ./scripts/complete_benchmark_workflow.sh
```

## 🛠️ Opção 2: Execução Manual (Passo a Passo)

### Passo 1: Converter Datasets

```bash
# Todos os formatos (recomendado)
python scripts/convert_dataset.py --all --workers 8

# Ou formatos específicos
python scripts/convert_dataset.py --formats xlsx docx --workers 8
python scripts/convert_dataset.py --formats json --workers 8
python scripts/convert_dataset.py --formats images --workers 4  # Mais lento
```

**Saída**: `benchmark/converted_datasets/{xlsx,docx,json,images}/`

### Passo 2: Analisar Estatísticas

```bash
# Dataset original
python scripts/analyze_dataset.py --dirs vulnnet_scans_openvas

# Dataset original + convertidos
python scripts/analyze_dataset.py --dirs \
    vulnnet_scans_openvas \
    benchmark/converted_datasets/xlsx \
    benchmark/converted_datasets/docx \
    benchmark/converted_datasets/json \
    benchmark/converted_datasets/images
```

**Saída**: `benchmark/dataset_statistics/`

### Passo 3: Executar Benchmarks

#### 3a. Dataset Original (CSV, XML, TXT, PDF)

```bash
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir vulnnet_scans_openvas \
    --runs 2 \
    --versions 2.0 3.0 \
    --strategies filtered hybrid standalone
```

#### 3b. Dataset XLSX

```bash
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/xlsx \
    --runs 2 \
    --versions 2.0 3.0 \
    --strategies filtered hybrid standalone
```

#### 3c. Dataset DOCX

```bash
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/docx \
    --runs 2 \
    --versions 2.0 3.0 \
    --strategies filtered hybrid standalone
```

#### 3d. Dataset JSON

```bash
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/json \
    --runs 2 \
    --versions 2.0 3.0 \
    --strategies filtered hybrid standalone
```

#### 3e. Dataset Images (OCR)

```bash
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/images \
    --runs 2 \
    --versions 2.0 3.0 \
    --strategies filtered hybrid standalone
```

## 📊 Verificar Resultados

### Estatísticas do Dataset

```bash
# Ver relatório Markdown (mais legível)
cat benchmark/dataset_statistics/dataset_statistics.md

# Ver CSV (para Excel)
head benchmark/dataset_statistics/dataset_statistics.csv

# Ver JSON (para programático)
python -m json.tool benchmark/dataset_statistics/dataset_statistics.json | head -50
```

### Resultados do Benchmark

```bash
# Últimas 10 linhas do CSV
tail -10 benchmark/results/benchmark_results.csv

# Contar linhas (total de runs)
wc -l benchmark/results/benchmark_results.csv

# Análise científica (se disponível)
python benchmark/analyze_benchmark_scientific.py
```

## 🔍 Verificação Rápida de Status

A qualquer momento, verifique o status com:

```bash
python scripts/check_dataset_status.py
```

Exemplo de saída:
```
======================================================================
DATASET STATUS CHECK
======================================================================

📁 Original Dataset
  Location: vulnnet_scans_openvas
  Total: 528 files, 28.3 MB
  Formats: 4

  By Format:
    .csv         132 files,      3.8 MB
    .pdf         132 files,     18.9 MB
    .txt         132 files,      4.2 MB
    .xml         132 files,     28.3 MB

📁 Converted: XLSX
  Location: benchmark/converted_datasets/xlsx
  Total: 132 files, 42.9 MB
  ...
```

## 📈 Análise dos Resultados

### Comparar Performance por Formato

```python
# Script rápido para análise
import pandas as pd

df = pd.read_csv('benchmark/results/benchmark_results.csv')

# Agrupar por formato
summary = df.groupby(['file_extension', 'version', 'strategy']).agg({
    'wall_clock_time_sec': ['mean', 'std', 'min', 'max'],
    'throughput_kb_per_sec': ['mean', 'std'],
    'max_resident_set_kb': ['mean', 'max']
}).round(2)

print(summary)
```

### Identificar Formato Mais Rápido

```bash
# Ver throughput médio por extensão (simplified)
awk -F',' 'NR>1 {sum[$3]+=$27; count[$3]++} END {for(ext in sum) print ext, sum[ext]/count[ext]}' \
    benchmark/results/benchmark_results.csv | sort -k2 -rn
```

## 🎨 Visualizações

### Gerar Gráficos (se tiver matplotlib)

```bash
# Histograma de tamanhos
python -c "
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('benchmark/dataset_statistics/dataset_files_detailed.csv')
df.groupby('extension')['size_kb'].plot.hist(alpha=0.5, legend=True)
plt.xlabel('Size (KB)')
plt.ylabel('Frequency')
plt.title('File Size Distribution by Format')
plt.savefig('size_distribution.png')
print('Saved: size_distribution.png')
"

# Throughput por formato
python -c "
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('benchmark/results/benchmark_results.csv')
df.boxplot(column='throughput_kb_per_sec', by='file_extension')
plt.suptitle('Throughput by File Format')
plt.xlabel('Format')
plt.ylabel('Throughput (KB/s)')
plt.savefig('throughput_by_format.png')
print('Saved: throughput_by_format.png')
"
```

## ⚠️ Troubleshooting Comum

### Problema: "No module named 'openpyxl'"

```bash
pip install openpyxl python-docx pdf2image pillow
```

### Problema: "pdftoppm: command not found"

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y poppler-utils

# macOS
brew install poppler

# Verificar
pdftoppm -h
```

### Problema: Conversão muito lenta

```bash
# Aumentar workers (CPU)
python scripts/convert_dataset.py --all --workers 16

# Converter por partes
python scripts/convert_dataset.py --formats xlsx --workers 8
python scripts/convert_dataset.py --formats docx --workers 8
python scripts/convert_dataset.py --formats json --workers 8
python scripts/convert_dataset.py --formats images --workers 4
```

### Problema: Falta de memória

```bash
# Reduzir workers
WORKERS=2 ./scripts/complete_benchmark_workflow.sh

# Ou converter sequencialmente
python scripts/convert_dataset.py --all --workers 1
```

### Problema: Disco cheio

```bash
# Ver uso
du -sh benchmark/converted_datasets/*

# Limpar formatos não usados
rm -rf benchmark/converted_datasets/images  # ~100 MB

# Comprimir resultados antigos
tar -czf benchmark_results_backup.tar.gz benchmark/results/
```

## 📝 Checklist Completo

```markdown
Pre-requisitos:
- [ ] Ambiente virtual ativado
- [ ] Dependências Python instaladas
- [ ] poppler-utils instalado
- [ ] Mínimo 500 MB livres
- [ ] Dataset original presente

Conversão:
- [ ] Convert_dataset.py executado
- [ ] XLSX gerado (132 arquivos)
- [ ] DOCX gerado (132 arquivos)
- [ ] JSON gerado (~264 arquivos)
- [ ] Images gerado (~132 diretórios)

Análise:
- [ ] analyze_dataset.py executado
- [ ] dataset_statistics.csv gerado
- [ ] dataset_statistics.md revisado

Benchmark:
- [ ] Original dataset benchmarked
- [ ] XLSX benchmarked
- [ ] DOCX benchmarked
- [ ] JSON benchmarked
- [ ] Images benchmarked
- [ ] Resultados revisados
```

## 🎓 Dicas Pro

1. **Use `screen` ou `tmux`** para sessões longas:
   ```bash
   screen -S benchmark
   ./scripts/complete_benchmark_workflow.sh
   # Ctrl+A, D para detach
   # screen -r benchmark para reattach
   ```

2. **Monitor progresso em tempo real**:
   ```bash
   watch -n 5 'python scripts/check_dataset_status.py'
   ```

3. **Log detalhado**:
   ```bash
   ./scripts/complete_benchmark_workflow.sh 2>&1 | tee full_workflow.log
   ```

4. **Backup antes de começar**:
   ```bash
   tar -czf vulnnet_backup.tar.gz vulnnet_scans_openvas/
   ```

---

**Tempo total estimado**: 30-90 minutos (dependendo de hardware e workers)  
**Espaço necessário**: ~300-500 MB  
**Resultado**: Dataset completo em 8+ formatos + estatísticas + benchmarks
