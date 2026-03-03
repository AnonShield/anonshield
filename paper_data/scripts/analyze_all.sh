#!/bin/bash
# =============================================================================
# analyze_all.sh — Run scientific analysis on all benchmark results in paper_data
#
# For each benchmark_results.csv found in paper_data/results/, this script
# generates analysis charts, statistics, and PDFs inside an analysis/ subfolder
# adjacent to the benchmark_results.csv file.
#
# Usage (from workspace root — no activation needed):
#   ./paper_data/scripts/analyze_all.sh              # standard analyses (1-14)
#   ./paper_data/scripts/analyze_all.sh --extended   # include extended (15-17)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PAPER_DATA="$WORKSPACE_ROOT/paper_data"
RESULTS_DIR="$PAPER_DATA/results"
ANALYZER="$WORKSPACE_ROOT/benchmark/analyze_benchmark_scientific.py"
OVERHEAD_CSV="$RESULTS_DIR/overhead_calibration__v3__all_strategies__10runs/benchmark_results.csv"
VENV_PY="$WORKSPACE_ROOT/.venv_benchmark/bin/python3"

# ── Auto-bootstrap venv if needed ────────────────────────────────────────
if [[ ! -x "$VENV_PY" ]]; then
    echo "  .venv_benchmark not found — running benchmark.py --force-setup..."
    python3 "$WORKSPACE_ROOT/benchmark/benchmark.py" --force-setup
    if [[ ! -x "$VENV_PY" ]]; then
        echo "ERROR: venv setup failed."
        exit 1
    fi
fi

# Extended flag
EXTENDED_FLAG=""
if [[ "${1:-}" == "--extended" ]]; then
    EXTENDED_FLAG="--extended"
    echo "Mode: EXTENDED analyses (1-17)"
else
    echo "Mode: STANDARD analyses (1-14)"
    echo "      Use --extended to include extended analyses (15-17)"
fi

# Sanity checks
if [[ ! -f "$ANALYZER" ]]; then
    echo "ERROR: analyzer not found at $ANALYZER"
    exit 1
fi
if [[ ! -f "$OVERHEAD_CSV" ]]; then
    echo "WARNING: overhead calibration data not found; overhead correction will be skipped."
    OVERHEAD_ARG=""
else
    OVERHEAD_ARG="--overhead $OVERHEAD_CSV"
fi

echo ""
echo "============================================================"
echo " AnonShield — Scientific Analysis Runner"
echo " Results dir : $RESULTS_DIR"
echo " Overhead    : ${OVERHEAD_ARG:-none}"
echo "============================================================"
echo ""

SUCCESS=0
FAILED=0
SKIPPED=0

# Iterate over every subdirectory in results/
for RUN_DIR in "$RESULTS_DIR"/*/; do
    [[ -d "$RUN_DIR" ]] || continue

    CSV="$RUN_DIR/benchmark_results.csv"
    OUTPUT_DIR="$RUN_DIR/analysis"
    RUN_NAME="$(basename "$RUN_DIR")"

    if [[ ! -f "$CSV" ]]; then
        echo "⚠  SKIPPED  $RUN_NAME  (no benchmark_results.csv)"
        ((SKIPPED++)) || true
        continue
    fi

    echo "------------------------------------------------------------"
    echo "→  Analyzing: $RUN_NAME"
    echo "------------------------------------------------------------"

    mkdir -p "$OUTPUT_DIR"

    # shellcheck disable=SC2086
    if "$VENV_PY" "$ANALYZER" \
            "$CSV" \
            -o "$OUTPUT_DIR" \
            $OVERHEAD_ARG \
            --pdf \
            $EXTENDED_FLAG; then
        echo "✅ SUCCESS: $RUN_NAME"
        ((SUCCESS++)) || true
    else
        echo "❌ FAILED:  $RUN_NAME"
        ((FAILED++)) || true
    fi
    echo ""
done

echo "============================================================"
echo " Summary"
echo "   Success : $SUCCESS"
echo "   Failed  : $FAILED"
echo "   Skipped : $SKIPPED"
echo "============================================================"

[[ $FAILED -eq 0 ]] || exit 1
