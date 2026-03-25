#!/bin/bash
#
# AnonLFI - Script de Benchmark CTCiber e CVE Dataset
#
# Executa benchmarks nas estratégias v3.0 com diferentes configurações:
# - Dados CTCiber com cache-size customizado (200000)
# - Dados CVE com configuração default
#

set -e  # Para em caso de erro

# Diretórios
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS_BASE="$BASE_DIR/benchmark/orchestrated_results"

# Retomar sessão existente (argumento) ou encontrar a última, ou criar nova
if [ -n "$1" ]; then
    SESSION_DIR="$1"
elif LATEST=$(ls -dt "$RESULTS_BASE"/session_ctciber_cve_* 2>/dev/null | head -1) && [ -n "$LATEST" ]; then
    SESSION_DIR="$LATEST"
    echo "[RESUMO] Retomando sessão existente: $SESSION_DIR"
else
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    SESSION_DIR="$RESULTS_BASE/session_ctciber_cve_$TIMESTAMP"
fi

# Arquivos de entrada
CTCIBER_CSV="$BASE_DIR/ignore/dados_CTCiber_AnonShield/consolidated_data.csv"
CTCIBER_JSON="$BASE_DIR/ignore/dados_CTCiber_AnonShield/consolidated_data.json"
CTCIBER_CONFIG="$BASE_DIR/anonymization_config.json"

CVE_CSV="$BASE_DIR/cve_dataset_anonimizados_stratified.csv"
CVE_JSON="$BASE_DIR/cve_dataset_anonimizados_stratified.json"
CVE_CONFIG="$BASE_DIR/anonymization_config_cve.json"

# Estratégias v3.0 (todas disponíveis)
STRATEGIES="standalone hybrid filtered presidio"

# Número de runs
RUNS=10

echo "=============================================================="
echo "ANONLFI BENCHMARK - CTCIBER & CVE DATASETS"
echo "=============================================================="
echo "Session: $SESSION_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

mkdir -p "$SESSION_DIR"

# ============================================================
# FASE 1: Benchmark CTCiber CSV (v3.0, max-cache-size 200000)
# ============================================================
echo ""
echo "[FASE 1] Benchmark CTCiber CSV (v3.0, max-cache-size 200000, $RUNS runs)"
echo "--------------------------------------------------------------"

PHASE1_DIR="$SESSION_DIR/01_ctciber_csv_cache200k"
mkdir -p "$PHASE1_DIR"

if [ -f "$CTCIBER_CSV" ]; then
    python3 "$BASE_DIR/benchmark/benchmark.py" \
        --benchmark \
        --file "$CTCIBER_CSV" \
        --versions 3.0 \
        --strategies $STRATEGIES \
        --runs $RUNS \
        --anonymization-config "$CTCIBER_CONFIG" \
        --max-cache-size 200000 \
        --cleanup-outputs \
        --results-dir "$PHASE1_DIR" \
        --continue-on-error
    
    echo "[FASE 1] Resultados em: $PHASE1_DIR"
else
    echo "[FASE 1] AVISO: Arquivo não encontrado: $CTCIBER_CSV"
fi

# ============================================================
# FASE 2: Benchmark CTCiber JSON (v3.0, max-cache-size 200000)
# ============================================================
echo ""
echo "[FASE 2] Benchmark CTCiber JSON (v3.0, max-cache-size 200000, $RUNS runs)"
echo "--------------------------------------------------------------"

PHASE2_DIR="$SESSION_DIR/02_ctciber_json_cache200k"
mkdir -p "$PHASE2_DIR"

if [ -f "$CTCIBER_JSON" ]; then
    python3 "$BASE_DIR/benchmark/benchmark.py" \
        --benchmark \
        --file "$CTCIBER_JSON" \
        --versions 3.0 \
        --strategies $STRATEGIES \
        --runs $RUNS \
        --anonymization-config "$CTCIBER_CONFIG" \
        --max-cache-size 200000 \
        --cleanup-outputs \
        --results-dir "$PHASE2_DIR" \
        --continue-on-error
    
    echo "[FASE 2] Resultados em: $PHASE2_DIR"
else
    echo "[FASE 2] AVISO: Arquivo não encontrado: $CTCIBER_JSON"
fi

# ============================================================
# FASE 3: Benchmark CVE CSV (v3.0, max-cache-size padrão)
# ============================================================
echo ""
echo "[FASE 3] Benchmark CVE CSV (v3.0, max-cache-size padrão, $RUNS runs)"
echo "--------------------------------------------------------------"

PHASE3_DIR="$SESSION_DIR/03_cve_csv_default"
mkdir -p "$PHASE3_DIR"

if [ -f "$CVE_CSV" ]; then
    python3 "$BASE_DIR/benchmark/benchmark.py" \
        --benchmark \
        --file "$CVE_CSV" \
        --versions 3.0 \
        --strategies $STRATEGIES \
        --runs $RUNS \
        --anonymization-config "$CVE_CONFIG" \
        --cleanup-outputs \
        --results-dir "$PHASE3_DIR" \
        --continue-on-error
    
    echo "[FASE 3] Resultados em: $PHASE3_DIR"
else
    echo "[FASE 3] AVISO: Arquivo não encontrado: $CVE_CSV"
fi

# ============================================================
# FASE 4: Benchmark CVE JSON (v3.0, max-cache-size padrão)
# ============================================================
echo ""
echo "[FASE 4] Benchmark CVE JSON (v3.0, max-cache-size padrão, $RUNS runs)"
echo "--------------------------------------------------------------"

PHASE4_DIR="$SESSION_DIR/04_cve_json_default"
mkdir -p "$PHASE4_DIR"

if [ -f "$CVE_JSON" ]; then
    python3 "$BASE_DIR/benchmark/benchmark.py" \
        --benchmark \
        --file "$CVE_JSON" \
        --versions 3.0 \
        --strategies $STRATEGIES \
        --runs $RUNS \
        --anonymization-config "$CVE_CONFIG" \
        --cleanup-outputs \
        --results-dir "$PHASE4_DIR" \
        --continue-on-error
    
    echo "[FASE 4] Resultados em: $PHASE4_DIR"
else
    echo "[FASE 4] AVISO: Arquivo não encontrado: $CVE_JSON"
fi

# ============================================================
# CONSOLIDAR RESULTADOS
# ============================================================
echo ""
echo "[CONSOLIDAÇÃO] Consolidando todos os resultados"
echo "--------------------------------------------------------------"

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
    echo "[CONSOLIDAÇÃO] Arquivo consolidado criado: $COMBINED_CSV"
    
    # Estatísticas básicas
    echo ""
    echo "Estatísticas:"
    echo "  Total de linhas: $(wc -l < "$COMBINED_CSV")"
    echo "  Runs bem-sucedidos: $(grep -c "SUCCESS" "$COMBINED_CSV" || echo 0)"
    echo "  Runs com falha: $(grep -c "FAILED\|ERROR" "$COMBINED_CSV" || echo 0)"
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
echo "  01_ctciber_csv_cache200k/   - CTCiber CSV (cache 200k)"
echo "  02_ctciber_json_cache200k/  - CTCiber JSON (cache 200k)"
echo "  03_cve_csv_default/         - CVE CSV (cache padrão)"
echo "  04_cve_json_default/        - CVE JSON (cache padrão)"
echo "  combined_results.csv        - Todos os resultados consolidados"
echo ""
echo "Configurações utilizadas:"
echo "  - Versão: 3.0"
echo "  - Estratégias: $STRATEGIES"
echo "  - Runs por teste: $RUNS"
echo "  - CTCiber max-cache-size: 200000"
echo "  - CVE max-cache-size: padrão"
echo ""
echo "=============================================================="
