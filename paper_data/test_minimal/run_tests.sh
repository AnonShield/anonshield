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
# Each run uses AnonShield v3.0, --strategies filtered, --runs 1.
# D2 and D3 test both without and with anonymization config.
#
# Expected runtime: ~5–20 min total (D1/D1C dominate due to PDF-OCR)
#
# USAGE (from workspace root — no activation needed, venv is auto-created):
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

# When running CPU-only, hide all CUDA devices from subprocesses so PyTorch
# does not attempt to use the GPU even if one is present (avoids CUDA kernel
# incompatibility errors on machines where CUDA is installed but misconfigured).
[[ "$CPU_ONLY" == "true" ]] && export CUDA_VISIBLE_DEVICES=""

# ── Python resolution ─────────────────────────────────────────────────────────
# benchmark.py creates .venv automatically on first run.
# convert_d1_to_d1c.py and analyze_benchmark_scientific.py need venv packages,
# so we use .venv/bin/python3 once it exists.
VENV_PY="$WORKSPACE_ROOT/.venv/bin/python3"

bootstrap_venv() {
    if [[ ! -x "$VENV_PY" ]]; then
        echo ""
        echo "  .venv not found — running benchmark.py --setup --force-setup to create it..."
        python3 "$BENCHMARK" --setup --force-setup $CPU_FLAG
        if [[ ! -x "$VENV_PY" ]]; then
            echo "  ERROR: venv setup failed. Check benchmark.py output above."
            exit 1
        fi
        echo "  venv ready: $VENV_PY"
    fi
}
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

# Bootstrap venv if needed (benchmark.py handles this automatically)
[[ "$DRY_RUN" == "false" ]] && bootstrap_venv

# ── Dataset setup — auto-populate D1 subset from full dataset ─────────────────
# D1_openvas (full, ~88 MB) is tracked in git at paper_data/datasets/D1_openvas/.
# Copy 3 lightweight targets into test_minimal/datasets/ if not already present.
FULL_D1="$WORKSPACE_ROOT/paper_data/datasets/D1_openvas"
TEST_D1="$DATASETS/D1_openvas"
D1_TARGETS=(openvas_alpine_3.7 openvas_centos_6 openvas_centos_7)

if [[ ! -d "$TEST_D1/${D1_TARGETS[0]}" ]]; then
    echo ""
    echo "  Setting up D1 test subset (copying 3 targets from $FULL_D1)..."
    if [[ ! -d "$FULL_D1" ]]; then
        echo "  ERROR: Full D1 dataset not found at $FULL_D1"
        echo "         Make sure paper_data/datasets/D1_openvas/ is present (it is tracked in git)."
        exit 1
    fi
    mkdir -p "$TEST_D1"
    for target in "${D1_TARGETS[@]}"; do
        cp -r "$FULL_D1/$target" "$TEST_D1/"
        echo "  Copied: $target"
    done
    echo "  D1 test subset ready."
elif [[ "$DRY_RUN" == "false" ]]; then
    echo ""
    echo "  D1 test subset already present — skipping copy."
fi

# ── D1 — OpenVAS (3 targets × 4 native formats) ──────────────────────────────
if [[ "$SKIP_D1" == "false" ]]; then
    section "D1 — OpenVAS native (3 targets: alpine_3.7, centos_6, centos_7)"
    echo "  AnonShield v3.0, filtered | 1 run"
    OUT="$RESULTS/D1_test"

    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --data-dir "$DATASETS/D1_openvas" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$OUT"

    # ── D1C — Generate converted formats from D1 ─────────────────────────────
    section "D1C — Generating converted formats from D1 (convert_d1_to_d1c.py)"
    echo "  CSV→XLSX  TXT→DOCX  XML→JSON  PDF→PDF-images  (3 targets)"
    CONVERT_SCRIPT="$WORKSPACE_ROOT/paper_data/scripts/convert_d1_to_d1c.py"
    D1C_DIR="$DATASETS/D1C_converted"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        echo "  \$ python3 $CONVERT_SCRIPT \\"
        echo "      --source $DATASETS/D1_openvas \\"
        echo "      --output $D1C_DIR \\"
        echo "      --workers 2"
    else
        echo ""
        echo "  \$ $VENV_PY $CONVERT_SCRIPT --source $DATASETS/D1_openvas --output $D1C_DIR --workers 2"
        if "$VENV_PY" "$CONVERT_SCRIPT" \
            --source "$DATASETS/D1_openvas" \
            --output "$D1C_DIR" \
            --workers 2; then
            PASS=$((PASS + 1))
        else
            FAIL=$((FAIL + 1))
            FAILED_STEPS+=("convert_d1_to_d1c.py")
            echo "  [FAILED] D1C generation failed — D1C benchmark steps will likely fail"
        fi
    fi

    # ── D1C — Converted formats ───────────────────────────────────────────────
    section "D1C — Converted formats (3 targets × xlsx, docx, json, pdf-images)"
    echo "  AnonShield v3.0, filtered | 1 run"
    OUT_D1C="$RESULTS/D1C_test"

    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --data-dir "$DATASETS/D1C_converted" \
        --versions 3.0 \
        --strategies filtered \
        --runs 1 \
        --clean \
        --results-dir "$OUT_D1C"
fi

# ── D2 — CAIS/CTCiber (500 rows CSV + 500 records JSON) ───────────────────────
if [[ "$SKIP_D2" == "false" ]]; then
    section "D2 — CAIS/CTCiber (500 rows/records, AnonShield, filtered, 1 run)"

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
        --max-cache-size 200000 \
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
        --max-cache-size 200000 \
        --results-dir "$RESULTS/D2_json_with_config_test"
fi

# ── D3 — Synthetic Mock CVE (500 rows CSV + 500 records JSON) ────────────────
if [[ "$SKIP_D3" == "false" ]]; then
    section "D3 — Synthetic Mock CVE (500 rows/records, AnonShield, filtered, 1 run)"

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

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "======================================================================"
echo "  AnonShield — Smoke Test Summary"
echo "======================================================================"
if [[ "$DRY_RUN" == "false" ]]; then
    TOTAL=$((PASS + FAIL))
    echo "  Steps passed : $PASS / $TOTAL"
    if [[ ${#FAILED_STEPS[@]} -gt 0 ]]; then
        echo "  Steps failed : $FAIL"
        echo ""
        echo "  Failed steps:"
        for s in "${FAILED_STEPS[@]}"; do
            echo "    - $s"
        done
        echo ""
        echo "  Results written to: $RESULTS/"
        echo "======================================================================"
        echo "  RESULT: FAILED"
        echo "======================================================================"
        exit 1
    else
        echo ""
        echo "  Results written to: $RESULTS/"
        echo "======================================================================"
        echo "  RESULT: ALL PASSED"
        echo "======================================================================"
        exit 0
    fi
else
    echo "======================================================================"
    exit 0
fi
