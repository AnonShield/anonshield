#!/bin/bash
# =============================================================================
# run_tests.sh — Minimal smoke test for all AnonShield benchmark scenarios
#
# Uses a tiny fraction of each dataset to verify the full pipeline works:
#   D1  — 3 OpenVAS targets × 4 native formats  (csv, txt, xml, pdf-text)
#   D1C — same 3 targets × 4 converted formats  (xlsx, docx, json, pdf-images)
#   D2  — 500 rows/records of CAIS/CTCiber CSV + JSON
#   D3  — 500 rows/records of synthetic CVE CSV + JSON
#
# Each run uses v3.0, --strategies filtered, --runs 1.
# D1 also tests v1.0 + v2.0 (default strategy).
# D2 and D3 test both without and with anonymization config.
#
# Expected runtime: ~5–20 min total (D1/D1C dominate due to PDF-OCR)
#
# USAGE (from workspace root):
#   source .venv_benchmark/bin/activate
#   ./paper_data/test_minimal/run_tests.sh
#
# FLAGS:
#   --skip-d1    Skip D1 and D1C
#   --skip-d2    Skip D2
#   --skip-d3    Skip D3
#   --cpu-only   Use CPU-only PyTorch (no CUDA); pass this on machines without
#                an NVIDIA GPU
#   --dry-run    Print commands without executing
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST="$SCRIPT_DIR"
DATASETS="$TEST/datasets"
RESULTS="$TEST/results"
BENCHMARK="$WORKSPACE_ROOT/benchmark/benchmark.py"
ANALYZER="$WORKSPACE_ROOT/benchmark/analyze_benchmark_scientific.py"

# ── Parse flags ──────────────────────────────────────────────────────────────
SKIP_D1=false
SKIP_D2=false
SKIP_D3=false
DRY_RUN=false
CPU_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --skip-d1)  SKIP_D1=true ;;
        --skip-d2)  SKIP_D2=true ;;
        --skip-d3)  SKIP_D3=true ;;
        --dry-run)  DRY_RUN=true ;;
        --cpu-only) CPU_ONLY=true ;;
        -h|--help)
            sed -n '2,30p' "$0" | grep '^#' | sed 's/^# \?//'
            exit 0 ;;
    esac
done
# Derive CPU_FLAG — forwarded to every benchmark.py invocation
CPU_FLAG=""
[[ "$CPU_ONLY" == "true" ]] && CPU_FLAG="--cpu-only"
# ── Helpers ──────────────────────────────────────────────────────────────────
PASS=0
FAIL=0
FAILED_STEPS=()

run_cmd() {
    echo ""
    echo "  \$ $*"
    if [[ "$DRY_RUN" == "false" ]]; then
        if "$@" $CPU_FLAG; then
            PASS=$((PASS + 1))
        else
            FAIL=$((FAIL + 1))
            FAILED_STEPS+=("$*")
            echo "  [FAILED] exit code $?"
        fi
    fi
}

section() {
    echo ""
    echo "======================================================================"
    echo "  $1"
    echo "======================================================================"
}

step() {
    echo ""
    echo "  ── $1"
}

# ── Sanity ───────────────────────────────────────────────────────────────────
if [[ ! -f "$BENCHMARK" ]]; then
    echo "ERROR: benchmark.py not found at $BENCHMARK"
    exit 1
fi

echo "======================================================================"
echo "  AnonShield — Minimal Smoke Test"
echo "  test_minimal : $TEST"
echo "  benchmark.py : $BENCHMARK"
[[ "$DRY_RUN" == "true" ]] && echo "  DRY RUN enabled"
[[ "$CPU_ONLY" == "true" ]] && echo "  CPU ONLY   : --cpu-only passed to all benchmark invocations"
echo "======================================================================"

# ── D1 — OpenVAS (3 targets × 4 native formats) ──────────────────────────────
if [[ "$SKIP_D1" == "false" ]]; then
    section "D1 — OpenVAS native (3 targets: alpine_3.7, centos_6, centos_7)"
    echo "  v1.0+v2.0 default, v3.0 filtered | 1 run"
    OUT="$RESULTS/D1_test"

    step "D1 — v1.0 + v2.0 (default strategy — no --strategies flag)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1_openvas" \
        --versions 1.0 2.0 \
        --runs 1 \
        --clean \
        --results-dir "$OUT"

    step "D1 — v3.0 (filtered)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1_openvas" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$OUT"

    # ── D1C — Converted formats ───────────────────────────────────────────────
    section "D1C — Converted formats (3 targets × xlsx, docx, json, pdf-images)"
    echo "  v1.0+v2.0 default, v3.0 filtered | 1 run"
    OUT_D1C="$RESULTS/D1C_test"

    step "D1C — v1.0 + v2.0 (default strategy — no --strategies flag)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1C_converted" \
        --versions 1.0 2.0 \
        --runs 1 \
        --clean \
        --results-dir "$OUT_D1C"

    step "D1C — v3.0 (filtered)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1C_converted" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$OUT_D1C"
fi

# ── D2 — CAIS/CTCiber (500 rows CSV + 500 records JSON) ───────────────────────
if [[ "$SKIP_D2" == "false" ]]; then
    section "D2 — CAIS/CTCiber (500 rows/records, v3.0, filtered, 1 run)"

    D2_CSV="$DATASETS/D2_cais/consolidated_data.csv"
    D2_JSON="$DATASETS/D2_cais/consolidated_data.json"
    D2_CFG="$DATASETS/D2_cais/anonymization_config.json"

    step "D2 CSV — without anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D2_CSV" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$RESULTS/D2_csv_without_config_test"

    step "D2 JSON — without anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D2_JSON" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$RESULTS/D2_json_without_config_test"

    step "D2 CSV — WITH anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D2_CSV" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --anonymization-config "$D2_CFG" \
        --results-dir "$RESULTS/D2_csv_with_config_test"

    step "D2 JSON — WITH anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D2_JSON" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --anonymization-config "$D2_CFG" \
        --results-dir "$RESULTS/D2_json_with_config_test"
fi

# ── D3 — Synthetic Mock CVE (500 rows CSV + 500 records JSON) ────────────────
if [[ "$SKIP_D3" == "false" ]]; then
    section "D3 — Synthetic Mock CVE (500 rows/records, v3.0, filtered, 1 run)"

    D3_CSV="$DATASETS/D3_mock_cve/cve_dataset_anonimizados_stratified.csv"
    D3_JSON="$DATASETS/D3_mock_cve/cve_dataset_anonimizados_stratified.json"
    D3_CFG="$DATASETS/D3_mock_cve/anonymization_config_cve.json"

    step "D3 CSV — without anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D3_CSV" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$RESULTS/D3_csv_without_config_test"

    step "D3 JSON — without anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D3_JSON" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$RESULTS/D3_json_without_config_test"

    step "D3 CSV — WITH anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D3_CSV" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --anonymization-config "$D3_CFG" \
        --results-dir "$RESULTS/D3_csv_with_config_test"

    step "D3 JSON — WITH anonymization config"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$D3_JSON" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --anonymization-config "$D3_CFG" \
        --results-dir "$RESULTS/D3_json_with_config_test"
fi

# ── Analysis phase ───────────────────────────────────────────────────────────
section "ANALYSIS — analyze_benchmark_scientific.py on every result"

if [[ ! -f "$ANALYZER" ]]; then
    echo "  WARNING: analyzer not found at $ANALYZER — skipping analysis phase"
else
    ANA_PASS=0
    ANA_FAIL=0

    for RUN_DIR in "$RESULTS"/*/; do
        [[ -d "$RUN_DIR" ]] || continue
        CSV="$RUN_DIR/benchmark_results.csv"
        ANA_OUT="$RUN_DIR/analysis"
        RUN_NAME="$(basename "$RUN_DIR")"

        if [[ ! -f "$CSV" ]]; then
            echo "  SKIP (no csv): $RUN_NAME"
            continue
        fi

        echo ""
        echo "  ── $RUN_NAME"
        if [[ "$DRY_RUN" == "false" ]]; then
            mkdir -p "$ANA_OUT"
            if python3 "$ANALYZER" "$CSV" -o "$ANA_OUT" --pdf; then
                echo "  [OK] analysis written to $ANA_OUT"
                ANA_PASS=$((ANA_PASS + 1))
            else
                echo "  [FAILED] analysis for $RUN_NAME"
                ANA_FAIL=$((ANA_FAIL + 1))
                FAILED_STEPS+=("analyze: $RUN_NAME")
                FAIL=$((FAIL + 1))
            fi
        else
            echo "  \$ python3 $ANALYZER $CSV -o $ANA_OUT --pdf"
        fi
    done

    if [[ "$DRY_RUN" == "false" ]]; then
        echo ""
        echo "  Analysis done — passed: $ANA_PASS  failed: $ANA_FAIL"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "======================================================================"
echo "  Smoke Test Complete"
if [[ "$DRY_RUN" == "false" ]]; then
    echo "  Benchmark steps passed : $PASS"
    echo "  Total failures         : $FAIL"
    if [[ ${#FAILED_STEPS[@]} -gt 0 ]]; then
        echo ""
        echo "  Failed steps:"
        for s in "${FAILED_STEPS[@]}"; do
            echo "    - $s"
        done
    fi
    echo ""
    echo "  Results written to: $RESULTS/"
    echo ""
    echo "  CSVs generated:"
    find "$RESULTS" -name "benchmark_results.csv" 2>/dev/null | sort | while read f; do
        rows=$(tail -n +2 "$f" | wc -l)
        echo "    $rows rows  $f"
    done
    echo ""
    echo "  Analysis folders:"
    find "$RESULTS" -type d -name "analysis" 2>/dev/null | sort | while read d; do
        cnt=$(find "$d" -type f | wc -l)
        echo "    $cnt files  $d"
    done
fi
echo "======================================================================"

[[ "$DRY_RUN" == "false" && "$FAIL" -gt 0 ]] && exit 1 || exit 0
