# Dataset Conversion & Analysis Tools

Ferramentas profissionais para converter e analisar o dataset `vulnnet_scans_openvas` em múltiplos formatos para benchmark do AnonShield.

## 📋 Visão Geral

Este conjunto de ferramentas permite:

1. **Converter datasets** para formatos adicionais (XLSX, DOCX, JSON, Images)
2. **Analisar estatísticas** detalhadas de tamanhos de arquivo por formato
3. **Gerar relatórios** em múltiplos formatos (CSV, JSON, Markdown)

## 🎯 Formatos Suportados

### Conversões Disponíveis

| Origem | Destino | Descrição |
|--------|---------|-----------|
| CSV | XLSX | Excel com formatação e ajuste automático de colunas |
| CSV | DOCX | Word com tabela formatada |
| CSV | JSON | Array de objetos JSON |
| XML | JSON | Estrutura XML preservada em JSON |
| PDF | Images | Uma imagem PNG por página (para teste de OCR) |

## 📦 Dependências

### Instalação

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências para conversão
pip install openpyxl python-docx pdf2image pillow

# Para PDF → Images, também é necessário poppler-utils (sistema)
sudo apt-get install poppler-utils  # Ubuntu/Debian
# ou
brew install poppler  # macOS
```

### Verificação de Dependências

Os scripts verificam automaticamente as dependências e informam quais conversões estão disponíveis.

## 🚀 Uso Rápido

### 1. Converter Dataset para Todos os Formatos

```bash
python scripts/convert_dataset.py --all
```

### 2. Analisar Estatísticas do Dataset Original

```bash
python scripts/analyze_dataset.py --dirs vulnnet_scans_openvas
```

### 3. Analisar Dataset Convertido

```bash
python scripts/analyze_dataset.py --dirs \
    vulnnet_scans_openvas \
    benchmark/converted_datasets/xlsx \
    benchmark/converted_datasets/docx \
    benchmark/converted_datasets/json \
    benchmark/converted_datasets/images
```

## 📖 Guia Detalhado

### Script de Conversão: `convert_dataset.py`

#### Opções Principais

```bash
# Converter apenas formatos específicos
python scripts/convert_dataset.py --formats xlsx docx

# Converter com diretórios customizados
python scripts/convert_dataset.py \
    --source /caminho/para/dados \
    --output /caminho/para/saida \
    --all

# Conversão paralela (mais rápido)
python scripts/convert_dataset.py --all --workers 8

# Forçar reconversão (ignorar arquivos existentes)
python scripts/convert_dataset.py --all --no-skip-existing

# Configurar qualidade das imagens
python scripts/convert_dataset.py \
    --formats images \
    --image-dpi 200 \
    --image-format png

# Modo verbose (debug)
python scripts/convert_dataset.py --all --verbose
```

#### Estrutura de Saída

```
benchmark/converted_datasets/
├── xlsx/          # Arquivos Excel
│   └── openvas_nginx_1.14/
│       └── openvas_nginx_1.14.xlsx
├── docx/          # Arquivos Word
│   └── openvas_nginx_1.14/
│       └── openvas_nginx_1.14.docx
├── json/          # Arquivos JSON
│   └── openvas_nginx_1.14/
│       ├── openvas_nginx_1.14.json      # Do CSV
│       └── openvas_nginx_1.14_xml.json  # Do XML
└── images/        # Imagens de PDF
    └── openvas_nginx_1.14/
        └── openvas_nginx_1.14/
            ├── page_001.png
            ├── page_002.png
            └── ...
```

#### Características Técnicas

- **Conversão Incremental**: Pula arquivos já convertidos (configurável)
- **Processamento Paralelo**: Múltiplos workers para velocidade
- **Tratamento de Erros**: Continua mesmo com falhas individuais
- **Logging Completo**: Log detalhado em `conversion.log`
- **Formatação Profissional**: Headers com cores, ajuste de colunas, etc.

### Script de Análise: `analyze_dataset.py`

#### Opções Principais

```bash
# Analisar diretório único
python scripts/analyze_dataset.py --dirs vulnnet_scans_openvas

# Analisar múltiplos diretórios
python scripts/analyze_dataset.py --dirs \
    vulnnet_scans_openvas \
    benchmark/converted_datasets/xlsx \
    benchmark/converted_datasets/docx

# Saída customizada
python scripts/analyze_dataset.py \
    --dirs vulnnet_scans_openvas \
    --output meu_relatorio

# Modo verbose
python scripts/analyze_dataset.py \
    --dirs vulnnet_scans_openvas \
    --verbose
```

#### Relatórios Gerados

O script gera 4 tipos de relatório:

1. **CSV Estatístico** (`dataset_statistics.csv`)
   - Estatísticas agregadas por extensão
   - Formato tabular para importação

2. **JSON Estruturado** (`dataset_statistics.json`)
   - Dados estruturados para processamento programático
   - Inclui metadados e totais

3. **Markdown** (`dataset_statistics.md`)
   - Relatório formatado e legível
   - Tabelas, distribuições, top 10
   - Ideal para documentação

4. **CSV Detalhado** (`dataset_files_detailed.csv`)
   - Lista completa de todos os arquivos
   - Path, extensão, tamanhos (bytes, KB, MB)
   - Ordenado por tamanho (maior → menor)

#### Estatísticas Calculadas

Para cada formato de arquivo:

- **Count**: Quantidade de arquivos
- **Total**: Tamanho total (bytes, KB, MB)
- **Min/Max**: Menor e maior arquivo
- **Mean**: Tamanho médio
- **Median**: Mediana dos tamanhos
- **Std Dev**: Desvio padrão
- **Distribuição**: Histograma de tamanhos

#### Exemplo de Saída Console

```
===============================================================
DATASET STATISTICS SUMMARY
===============================================================

Extension        Count   Total (MB)   Min (KB)   Max (KB)  Mean (KB)
------------ -------- ------------ ---------- ---------- ----------
.csv              132        3.85       12.3      145.2       29.9
.docx             132       45.23       85.4      523.8      342.7
.json             264       12.45       28.9      312.1       47.1
.pdf              132       18.92       89.5      456.3      143.3
.png              528       95.34      125.6      890.2      180.5
.txt              132        4.23       15.8      178.9       32.0
.xlsx             132       42.87       78.2      498.7      324.8
.xml              132       28.34       98.7      678.4      214.7
------------ -------- ------------ ---------- ---------- ----------
TOTAL            1584      251.23
```

## 🔧 Integração com Benchmark

### Workflow Completo

```bash
# 1. Converter dataset
python scripts/convert_dataset.py --all --workers 8

# 2. Gerar estatísticas
python scripts/analyze_dataset.py \
    --dirs vulnnet_scans_openvas \
           benchmark/converted_datasets/xlsx \
           benchmark/converted_datasets/docx \
           benchmark/converted_datasets/json \
           benchmark/converted_datasets/images

# 3. Rodar benchmarks com TODOS os formatos
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir vulnnet_scans_openvas \
    --runs 2 \
    --versions 1.0 2.0 3.0 \
    --strategies filtered hybrid standalone

# 3b. Também rodar com datasets convertidos
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/xlsx \
    --runs 2 \
    --versions 2.0 3.0

python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/docx \
    --runs 2 \
    --versions 2.0 3.0

python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/json \
    --runs 2 \
    --versions 2.0 3.0

python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/images \
    --runs 2 \
    --versions 2.0 3.0
```

### Formatos Suportados por Versão

| Versão | CSV | TXT | XML | XLSX | DOCX | JSON | PDF | Images |
|--------|-----|-----|-----|------|------|------|-----|--------|
| v1.0   | ✓   | ✓   | ✓   | ✓    | ✓    | ✗    | ✗   | ✗      |
| v2.0   | ✓   | ✓   | ✓   | ✓    | ✓    | ✓    | ✓   | ✓      |
| AnonShield   | ✓   | ✓   | ✓   | ✓    | ✓    | ✓    | ✓   | ✓      |

**Nota**: v1.0 suporta 5 formatos, v2.0 e AnonShield suportam 13-19 formatos.

## 🏗️ Arquitetura dos Scripts

### Princípios de Design (SOLID)

1. **Single Responsibility**: Cada classe tem uma responsabilidade única
   - `FileConverter`: Interface para conversores
   - `CSVToXLSXConverter`: Conversão específica CSV→XLSX
   - `DatasetConverter`: Orquestração geral

2. **Open/Closed**: Extensível sem modificar código existente
   - Novos conversores: implementar `FileConverter`
   - Adicionar ao `_initialize_converters()`

3. **Liskov Substitution**: Conversores são intercambiáveis
   - Mesma interface `convert()`
   - Mesmo tipo de retorno `ConversionResult`

4. **Interface Segregation**: Interfaces mínimas
   - `can_convert()`: verifica aplicabilidade
   - `convert()`: realiza conversão
   - `get_output_path()`: determina destino

5. **Dependency Inversion**: Depende de abstrações
   - `FileConverter` é abstrato (ABC)
   - Implementações concretas injetadas

### Robustez e Qualidade

- **Type Safety**: Type hints em todas as funções
- **Error Handling**: Try-except com logging detalhado
- **Progress Tracking**: Feedback em tempo real
- **Resumable**: Skip de arquivos já convertidos
- **Logging**: Níveis INFO/DEBUG com timestamps
- **Testing Ready**: Classes isoladas, fáceis de testar

## 📊 Casos de Uso

### Caso 1: Benchmark Completo Multi-Formato

**Objetivo**: Testar performance em XLSX, DOCX e JSON.

```bash
# 1. Converter
python scripts/convert_dataset.py --formats xlsx docx json --workers 8

# 2. Estatísticas
python scripts/analyze_dataset.py \
    --dirs vulnnet_scans_openvas \
           benchmark/converted_datasets/xlsx \
           benchmark/converted_datasets/docx \
           benchmark/converted_datasets/json

# 3. Benchmark de cada formato
for format_dir in xlsx docx json; do
    python benchmark/benchmark.py \
        --benchmark \
        --directory-mode \
        --data-dir benchmark/converted_datasets/$format_dir \
        --runs 2 \
        --versions 2.0 3.0
done
```

### Caso 2: Teste de OCR (PDF → Images)

**Objetivo**: Avaliar performance de OCR em v2.0 e AnonShield.

```bash
# 1. Gerar imagens dos PDFs
python scripts/convert_dataset.py \
    --formats images \
    --image-dpi 150 \
    --workers 4

# 2. Benchmark OCR
python benchmark/benchmark.py \
    --benchmark \
    --directory-mode \
    --data-dir benchmark/converted_datasets/images \
    --runs 2 \
    --versions 2.0 3.0
```

### Caso 3: Análise de Distribuição de Tamanhos

**Objetivo**: Entender distribuição de tamanhos antes de definir targets de regression.

```bash
# Analisar dataset original
python scripts/analyze_dataset.py \
    --dirs vulnnet_scans_openvas \
    --verbose

# Ver relatório Markdown com histogramas
cat benchmark/dataset_statistics/dataset_statistics.md
```

## 🔍 Troubleshooting

### Problema: "openpyxl not installed"

**Solução**:
```bash
pip install openpyxl
```

### Problema: "pdf2image conversion failed"

**Causa**: Falta poppler-utils no sistema.

**Solução**:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Verificar
pdftoppm -h
```

### Problema: Conversão lenta

**Solução**: Aumentar workers
```bash
python scripts/convert_dataset.py --all --workers 16
```

### Problema: Memória insuficiente

**Solução**: Reduzir workers ou processar por lotes
```bash
# Converter apenas um formato por vez
python scripts/convert_dataset.py --formats xlsx --workers 4
python scripts/convert_dataset.py --formats docx --workers 4
```

### Problema: Arquivos não encontrados

**Solução**: Verificar caminhos
```bash
# Listar arquivos fonte
ls -R vulnnet_scans_openvas | grep -E '\.(csv|xml|pdf)$'

# Verificar saída
ls -R benchmark/converted_datasets/
```

## 📈 Performance Esperada

### Tempos de Conversão (estimativa)

| Formato | Arquivos | Workers | Tempo Aproximado |
|---------|----------|---------|------------------|
| XLSX    | 132      | 4       | ~2-3 min         |
| DOCX    | 132      | 4       | ~3-4 min         |
| JSON    | 264      | 4       | ~1-2 min         |
| Images  | 132 PDFs | 4       | ~10-15 min       |

**Total (todos os formatos)**: ~15-25 minutos com 4 workers.

### Espaço em Disco

| Formato     | Tamanho Esperado |
|-------------|------------------|
| Original    | ~30 MB           |
| XLSX        | ~40-50 MB        |
| DOCX        | ~45-55 MB        |
| JSON (CSV)  | ~12-15 MB        |
| JSON (XML)  | ~30-35 MB        |
| Images      | ~90-100 MB       |
| **Total**   | **~250-280 MB**  |

## 🎓 Melhores Práticas

1. **Sempre gerar estatísticas** antes e depois da conversão
2. **Usar `--workers`** para acelerar (mas cuidado com memória)
3. **Verificar `conversion.log`** se houver falhas
4. **Fazer backup** do dataset original antes de grandes operações
5. **Usar `--no-skip-existing`** apenas quando necessário (reconversão é lenta)

## 🚦 Checklist de Execução

```markdown
- [ ] Instalar dependências (`openpyxl`, `python-docx`, `pdf2image`, `poppler-utils`)
- [ ] Verificar espaço em disco (mínimo 300 MB livres)
- [ ] Gerar estatísticas do dataset original
- [ ] Converter para formatos desejados
- [ ] Gerar estatísticas dos datasets convertidos
- [ ] Executar benchmarks por formato
- [ ] Comparar resultados entre formatos
- [ ] Documentar findings
```

## 📝 Notas Importantes

- **Conversões são idempotentes**: Rodar múltiplas vezes é seguro (skip automático)
- **Logs são preservados**: `conversion.log` tem histórico completo
- **Erros não param o processo**: Falhas individuais são registradas e o processo continua
- **Estrutura de diretórios é preservada**: Mantém organização original

## 🤝 Contribuindo

Para adicionar novos conversores:

1. Criar classe que herda `FileConverter`
2. Implementar `can_convert()`, `get_output_path()`, `convert()`
3. Adicionar em `_initialize_converters()`
4. Documentar no README

Exemplo:
```python
class TXTToPDFConverter(FileConverter):
    TARGET_FORMAT = "pdf"
    
    def can_convert(self, source_file: Path) -> bool:
        return source_file.suffix.lower() == ".txt" and REPORTLAB_AVAILABLE
    
    def get_output_path(self, source_file: Path) -> Path:
        # implementar
        pass
    
    def convert(self, source_file: Path) -> ConversionResult:
        # implementar
        pass
```

---

**Desenvolvido por**: AnonShield Team  
**Data**: Fevereiro 2026  
**Licença**: Mesma do projeto principal
