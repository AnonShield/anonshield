#!/bin/bash
#
# AnonLFI - Script de Benchmark Completo
#
# Executa todas as fases de benchmark com resultados em pastas separadas.
# Resumível: pode ser interrompido e retomado de onde parou.
#

set -e  # Para em caso de erro

# Diretórios
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS_BASE="$BASE_DIR/benchmark/orchestrated_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SESSION_DIR="$RESULTS_BASE/session_$TIMESTAMP"

# Arquivos de entrada
CVE_DATASET="$BASE_DIR/cve_dataset_anonimizados_stratified.json"
VULNNET_DIR="$BASE_DIR/vulnnet_scans_openvas"

# Estratégias v3.0 (sem SLM - muito lento para benchmark)
STRATEGIES="standalone hybrid filtered presidio"

echo "=============================================================="
echo "ANONLFI BENCHMARK SUITE"
echo "=============================================================="
echo "Session: $SESSION_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

mkdir -p "$SESSION_DIR"

# ============================================================
# FASE 1: Benchmark CVE Dataset (v3.0, 10 runs)
# ============================================================
echo ""
echo "[FASE 1] Benchmark CVE Dataset (v3.0, 10 runs)"
echo "--------------------------------------------------------------"

PHASE1_DIR="$SESSION_DIR/01_cve_dataset_v3_10runs"
mkdir -p "$PHASE1_DIR"

python3 "$BASE_DIR/benchmark/benchmark.py" \
    --benchmark \
    --file "$CVE_DATASET" \
    --versions 3.0 \
    --strategies $STRATEGIES \
    --runs 10 \
    --results-dir "$PHASE1_DIR" \
    --continue-on-error

echo "[FASE 1] Concluída. Resultados em: $PHASE1_DIR"

# ============================================================
# FASE 2: Calibração de Overhead (todas versões, 10 runs)
# ============================================================
echo ""
echo "[FASE 2] Calibração de Overhead (todas versões, 10 runs)"
echo "--------------------------------------------------------------"

PHASE2_DIR="$SESSION_DIR/02_overhead_calibration_10runs"
mkdir -p "$PHASE2_DIR"

python3 "$BASE_DIR/benchmark/benchmark.py" \
    --calibrate-overhead \
    --strategies $STRATEGIES \
    --runs 10 \
    --results-dir "$PHASE2_DIR" \
    --continue-on-error

echo "[FASE 2] Concluída. Resultados em: $PHASE2_DIR"

# ============================================================
# FASE 3: Coleta de Regressão (todas versões, 3 runs, até 1MB)
# ============================================================
echo ""
echo "[FASE 3] Coleta de Dados de Regressão (todas versões, 3 runs, até 1MB)"
echo "--------------------------------------------------------------"

PHASE3_DIR="$SESSION_DIR/03_regression_3runs"
mkdir -p "$PHASE3_DIR"

# 3a: Arquivos existentes do vulnnet (csv, pdf, txt, xml)
echo "[FASE 3a] Regressão com arquivos vulnnet..."
python3 "$BASE_DIR/benchmark/benchmark.py" \
    --regression \
    --regression-dir "$VULNNET_DIR" \
    --regression-max-file-mb 1 \
    --strategies $STRATEGIES \
    --runs 3 \
    --results-dir "$PHASE3_DIR" \
    --continue-on-error

# 3b: JSON (gera subsets do CVE dataset)
echo "[FASE 3b] Regressão com JSON..."
python3 "$BASE_DIR/benchmark/benchmark.py" \
    --regression \
    --regression-source "$CVE_DATASET" \
    --regression-max-file-mb 1 \
    --strategies $STRATEGIES \
    --runs 3 \
    --results-dir "$PHASE3_DIR" \
    --continue-on-error

# 3c: XLSX (gerado a partir de CSV) e DOCX (gerado a partir de TXT)
echo "[FASE 3c] Regressão com XLSX e DOCX (gerados)..."
# Pega um CSV e um TXT do vulnnet para gerar xlsx e docx
SAMPLE_CSV=$(find "$VULNNET_DIR" -name "*.csv" -size +10k | head -1)
SAMPLE_TXT=$(find "$VULNNET_DIR" -name "*.txt" -size +10k | head -1)

if [ -n "$SAMPLE_CSV" ] && [ -n "$SAMPLE_TXT" ]; then
    python3 "$BASE_DIR/benchmark/benchmark.py" \
        --regression \
        --regression-source "$SAMPLE_CSV,$SAMPLE_TXT" \
        --regression-max-file-mb 1 \
        --strategies $STRATEGIES \
        --runs 3 \
        --results-dir "$PHASE3_DIR" \
        --continue-on-error
fi

echo "[FASE 3] Concluída. Resultados em: $PHASE3_DIR"

# ============================================================
# FASE 4: Benchmark Single-File (vulnnet, 1 run, todas versões)
# ============================================================
echo ""
echo "[FASE 4] Benchmark Single-File Completo (1 run)"
echo "--------------------------------------------------------------"

PHASE4_DIR="$SESSION_DIR/04_full_single_file_1run"
mkdir -p "$PHASE4_DIR"

python3 "$BASE_DIR/benchmark/benchmark.py" \
    --benchmark \
    --data-dir "$VULNNET_DIR" \
    --strategies $STRATEGIES \
    --runs 1 \
    --results-dir "$PHASE4_DIR" \
    --continue-on-error

echo "[FASE 4] Concluída. Resultados em: $PHASE4_DIR"

# ============================================================
# FASE 5: Benchmark Directory-Mode (vulnnet, 1 run, todas versões)
# ============================================================
echo ""
echo "[FASE 5] Benchmark Directory-Mode (todas versões, 1 run)"
echo "--------------------------------------------------------------"

PHASE5_DIR="$SESSION_DIR/05_full_directory_mode_1run"
mkdir -p "$PHASE5_DIR"

python3 "$BASE_DIR/benchmark/benchmark.py" \
    --benchmark \
    --directory-mode \
    --data-dir "$VULNNET_DIR" \
    --strategies $STRATEGIES \
    --runs 1 \
    --results-dir "$PHASE5_DIR" \
    --continue-on-error

echo "[FASE 5] Concluída. Resultados em: $PHASE5_DIR"

# ============================================================
# GERAR ESTIMATIVAS
# ============================================================
echo ""
echo "[ESTIMATIVAS] Gerando estimativas com base nos resultados"
echo "--------------------------------------------------------------"

# Combinar todos os CSVs para estimativa
COMBINED_CSV="$SESSION_DIR/combined_results.csv"
first=true
for csv in "$SESSION_DIR"/*/benchmark_results.csv; do
    if [ -f "$csv" ]; then
        if $first; then
            cat "$csv" > "$COMBINED_CSV"
            first=false
        else
            tail -n +2 "$csv" >> "$COMBINED_CSV"
        fi
    fi
done

if [ -f "$COMBINED_CSV" ]; then
    python3 "$BASE_DIR/benchmark/estimate.py" \
        --data-dir "$VULNNET_DIR" \
        --results-csv "$COMBINED_CSV" \
        --output "$SESSION_DIR/ESTIMATES.md" \
        --runs 10
    echo "[ESTIMATIVAS] Relatório salvo em: $SESSION_DIR/ESTIMATES.md"
fi

# ============================================================
# RESUMO FINAL
# ============================================================
echo ""
echo "=============================================================="
echo "BENCHMARK COMPLETO"
echo "=============================================================="
echo ""
echo "Todos os resultados em: $SESSION_DIR"
echo ""
echo "Estrutura:"
echo "  01_cve_dataset_v3_10runs/      - Benchmark CVE dataset"
echo "  02_overhead_calibration_v3_10runs/ - Calibração overhead"
echo "  03_regression_v3_3runs/        - Dados de regressão"
echo "  04_full_single_file_1run/      - Benchmark single-file"
echo "  05_full_directory_mode_1run/   - Benchmark directory-mode"
echo "  combined_results.csv           - Todos os resultados"
echo "  ESTIMATES.md                   - Estimativas de tempo"
echo ""
echo "=============================================================="
