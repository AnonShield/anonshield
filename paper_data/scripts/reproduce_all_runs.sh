#!/bin/bash
# =============================================================================
# reproduce_all_runs.sh — Full benchmark reproduction workflow
#
# Reproduces ALL benchmark runs from the AnonShield paper, writing results
# to the same paper_data/results/ directory structure so results can be
# compared directly against the archived data.
#
# Estimated total runtime:  ~60–80 hours (dominated by D2/D3 without-config)
# Disk space required:      ~5 GB free
#
# DATASETS
#   D1  — OpenVAS scans (130 targets × 4 formats: CSV, TXT, XML, PDF-text)
#   D1C — Converted formats (130 targets × 4: XLSX, DOCX, JSON, PDF-images)
#   D2  — CAIS/CTCiber Tenable consolidated scan (consolidated_data.csv/.json)
#   D3  — Synthetic Mock CVE dataset (cve_dataset_anonimizados_stratified.csv/.json)
#
# RUNS REPRODUCED
#   • D1  : v1.0 + v2.0 (default) + v3.0 (filtered/hybrid/standalone/presidio), 2 runs each
#   • D1C : same version/strategy matrix, 2 runs each
#   • D2  : v3.0, 4 strategies, 10 runs — WITHOUT anonymization config (~30 min/run)
#   • D2  : v3.0, 4 strategies, 10 runs — WITH    anonymization config (~3 min/run)
#   • D3  : v3.0, 4 strategies, 10 runs — WITHOUT anonymization config (~4 min/run)
#   • D3  : v3.0, 4 strategies, 10 runs — WITH    anonymization config (~15 sec/run)
#   • Overhead calibration: v3.0, all strategies, 10 runs
#
# USAGE (from workspace root — no activation needed, venv is auto-created):
#   ./paper_data/scripts/reproduce_all_runs.sh [--skip-d1] [--skip-d2] [--skip-d3] [--cpu-only]
#
# FLAGS
#   --skip-d1         Skip D1 and D1C runs (long, multi-hour)
#   --skip-d2         Skip D2 runs (includes ~50h without-config run)
#   --skip-d3         Skip D3 runs
#   --skip-overhead   Skip overhead calibration
#   --cpu-only        Install and run with CPU-only PyTorch (no CUDA); use on
#                     machines without an NVIDIA GPU
#   --dry-run         Print commands without executing
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PAPER_DATA="$WORKSPACE_ROOT/paper_data"
DATASETS="$PAPER_DATA/datasets"
RESULTS="$PAPER_DATA/results"
CONFIGS="$PAPER_DATA/configs"
BENCHMARK="$WORKSPACE_ROOT/benchmark/benchmark.py"

# ── Parse flags ──────────────────────────────────────────────────────────────
SKIP_D1=false
SKIP_D2=false
SKIP_D3=false
SKIP_OVERHEAD=false
DRY_RUN=false
CPU_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --skip-d1)      SKIP_D1=true ;;
        --skip-d2)      SKIP_D2=true ;;
        --skip-d3)      SKIP_D3=true ;;
        --skip-overhead) SKIP_OVERHEAD=true ;;
        --dry-run)      DRY_RUN=true ;;
        --cpu-only)     CPU_ONLY=true ;;
        -h|--help)
            sed -n '2,50p' "$0" | grep '^#' | sed 's/^# \?//'
            exit 0 ;;
    esac
done

# Derive CPU_FLAG — forwarded to every benchmark.py invocation
CPU_FLAG=""
[[ "$CPU_ONLY" == "true" ]] && CPU_FLAG="--cpu-only"

# ── Python resolution ─────────────────────────────────────────────────────────
# benchmark.py manages its own venvs and is called with system python3.
# convert_d1_to_d1c.py and analyze_all.sh need packages from .venv_benchmark.
VENV_PY="$WORKSPACE_ROOT/.venv_benchmark/bin/python3"

bootstrap_venv() {
    if [[ ! -x "$VENV_PY" ]]; then
        echo ""
        echo "  .venv_benchmark not found — running benchmark.py --setup --force-setup..."
        python3 "$BENCHMARK" --setup --force-setup $CPU_FLAG
        if [[ ! -x "$VENV_PY" ]]; then
            echo "  ERROR: venv setup failed."
            exit 1
        fi
    fi
}

# ── Helpers ───────────────────────────────────────────────────────────────────
run_cmd() {
    echo ""
    echo "  \$ $*"
    if [[ "$DRY_RUN" == "false" ]]; then
        "$@"
    fi
}

print_section() {
    echo ""
    echo "======================================================================"
    echo "  $1"
    echo "======================================================================"
}

print_step() {
    echo ""
    echo "  ── $1"
}

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [[ ! -f "$BENCHMARK" ]]; then
    echo "ERROR: benchmark.py not found at $BENCHMARK"
    exit 1
fi

# Bootstrap venv if not yet created (benchmark.py handles this automatically)
[[ "$DRY_RUN" == "false" ]] && bootstrap_venv

echo "======================================================================"
echo "  AnonShield — Full Benchmark Reproduction"
echo "  Workspace  : $WORKSPACE_ROOT"
echo "  paper_data : $PAPER_DATA"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "  DRY RUN    : commands will be printed but not executed"
fi
[[ "$CPU_ONLY" == "true" ]] && echo "  CPU ONLY   : --cpu-only passed to all benchmark invocations"
echo "======================================================================"

# ── OVERHEAD CALIBRATION ─────────────────────────────────────────────────────
if [[ "$SKIP_OVERHEAD" == "false" ]]; then
    print_section "OVERHEAD CALIBRATION (v3.0 | 4 strategies | 10 runs | ~5 min)"

    OUT="$RESULTS/overhead_calibration__v3__all_strategies__10runs"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --calibrate-overhead \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        $CPU_FLAG \
        --results-dir "$OUT"
fi

# ── D1 — OpenVAS scans ───────────────────────────────────────────────────────
if [[ "$SKIP_D1" == "false" ]]; then
    print_section "D1 — OpenVAS Scans (130 targets × 4 native formats, v1+v2+v3, 2 runs)"
    echo "  Input : $DATASETS/D1_openvas/"
    echo "  Est.  : several hours (130 × 4 × 6 combos × 2 runs)"

    OUT="$RESULTS/D1_openvas__v1_v2_v3__all_strategies__1run"
    mkdir -p "$OUT"

    # v1.0 + v2.0 — Strategy.DEFAULT is used internally; no --strategies flag accepted
    print_step "D1 — v1.0 and v2.0 (built-in default strategy)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1_openvas" \
        --versions 1.0 2.0 \
        --runs 2 \
        $CPU_FLAG \
        --results-dir "$OUT"

    # v3.0 — four strategies
    print_step "D1 — v3.0 (filtered, hybrid, standalone, presidio)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1_openvas" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 2 \
        $CPU_FLAG \
        --results-dir "$OUT"

    # ── D1C — Generate converted formats from D1 ─────────────────────────────
    print_section "D1C — Generating converted formats from D1 (convert_d1_to_d1c.py)"
    echo "  CSV→XLSX  TXT→DOCX  XML→JSON  PDF→PDF-images  (130 targets, ~20–60 min)"
    echo "  Skip with: ls $DATASETS/D1C_converted/ to verify already generated"
    CONVERT_SCRIPT="$SCRIPT_DIR/convert_d1_to_d1c.py"
    if [[ -d "$DATASETS/D1C_converted/xlsx" && -d "$DATASETS/D1C_converted/pdf_images" ]]; then
        echo "  D1C_converted/ already exists — skipping conversion (use --force to re-run)"
    else
        run_cmd "$VENV_PY" "$CONVERT_SCRIPT" \
            --source "$DATASETS/D1_openvas" \
            --output "$DATASETS/D1C_converted" \
            --workers 4
    fi

    # ── D1C — Converted formats ───────────────────────────────────────────────
    print_section "D1C — Converted Formats (130 targets × 4 converted formats, v1+v2+v3, 2 runs)"
    echo "  Input : $DATASETS/D1C_converted/"
    echo "  Est.  : several hours (D1C PDF-images are large)"

    OUT_D1C="$RESULTS/D1C_converted__v1_v2_v3__all_strategies__1run"
    mkdir -p "$OUT_D1C"

    print_step "D1C — v1.0 and v2.0 (built-in default strategy)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1C_converted" \
        --versions 1.0 2.0 \
        --runs 2 \
        $CPU_FLAG \
        --results-dir "$OUT_D1C"

    print_step "D1C — v3.0 (filtered, hybrid, standalone, presidio)"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --directory-mode \
        --data-dir "$DATASETS/D1C_converted" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 2 \
        $CPU_FLAG \
        --results-dir "$OUT_D1C"
fi

# ── D2 — CAIS/CTCiber Tenable ─────────────────────────────────────────────
if [[ "$SKIP_D2" == "false" ]]; then

    # D2 — CSV — WITHOUT anonymization config
    # WARNING: ~30 min per run × 10 runs × 4 strategies = ~20 hours
    print_section "D2 CSV — WITHOUT anonymization config (v3.0 | 4 strategies | 10 runs | ~20h)"
    echo "  Input : $DATASETS/D2_cais_original/consolidated_data.csv"
    echo "  Config: NONE (cold NLP model load on each run)"

    OUT="$RESULTS/D2_cais_csv__v3__all_strategies__10runs__without_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D2_cais_original/consolidated_data.csv" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        $CPU_FLAG \
        --results-dir "$OUT"

    # D2 — JSON — WITHOUT anonymization config (~15 min per run, JSON is smaller)
    print_section "D2 JSON — WITHOUT anonymization config (v3.0 | 4 strategies | 10 runs | ~10h)"
    echo "  Input : $DATASETS/D2_cais_original/consolidated_data.json"

    OUT="$RESULTS/D2_cais_json__v3__all_strategies__10runs__without_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D2_cais_original/consolidated_data.json" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        $CPU_FLAG \
        --results-dir "$OUT"

    # D2 — CSV — WITH anonymization config (pre-loaded entity cache)
    # ~13 sec per run — the anonymization_config enables a 200k-entity cache
    print_section "D2 CSV — WITH anonymization config (v3.0 | 4 strategies | 10 runs | ~9 min)"
    echo "  Input : $DATASETS/D2_cais_original/consolidated_data.csv"
    echo "  Config: $CONFIGS/anonymization_config.json  (cache=200k entities)"

    OUT="$RESULTS/D2_cais_csv__v3__all_strategies__10runs__with_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D2_cais_original/consolidated_data.csv" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        --anonymization-config "$CONFIGS/anonymization_config.json" \
        $CPU_FLAG \
        --results-dir "$OUT"

    # D2 — JSON — WITH anonymization config
    print_section "D2 JSON — WITH anonymization config (v3.0 | 4 strategies | 10 runs | ~12 min)"
    echo "  Input : $DATASETS/D2_cais_original/consolidated_data.json"
    echo "  Config: $CONFIGS/anonymization_config.json"

    OUT="$RESULTS/D2_cais_json__v3__all_strategies__10runs__with_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D2_cais_original/consolidated_data.json" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        --anonymization-config "$CONFIGS/anonymization_config.json" \
        $CPU_FLAG \
        --results-dir "$OUT"
fi

# ── D3 — Synthetic Mock CVE dataset ──────────────────────────────────────────
if [[ "$SKIP_D3" == "false" ]]; then

    # D3 — CSV — WITHOUT anonymization config (~4 min per run)
    print_section "D3 CSV — WITHOUT anonymization config (v3.0 | 4 strategies | 10 runs | ~2.7h)"
    echo "  Input : $DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.csv"

    OUT="$RESULTS/D3_mock_cve_csv__v3__all_strategies__10runs__without_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.csv" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        $CPU_FLAG \
        --results-dir "$OUT"

    # D3 — JSON — WITHOUT anonymization config
    print_section "D3 JSON — WITHOUT anonymization config (v3.0 | 4 strategies | 10 runs | ~2.5h)"
    echo "  Input : $DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.json"

    OUT="$RESULTS/D3_mock_cve_json__v3__all_strategies__10runs__without_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.json" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        $CPU_FLAG \
        --results-dir "$OUT"

    # D3 — CSV — WITH anonymization config (~8.7 sec per run)
    print_section "D3 CSV — WITH anonymization config (v3.0 | 4 strategies | 10 runs | ~6 min)"
    echo "  Input : $DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.csv"
    echo "  Config: $CONFIGS/anonymization_config_cve.json  (cache=200k entities)"

    OUT="$RESULTS/D3_mock_cve_csv__v3__all_strategies__10runs__with_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.csv" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        --anonymization-config "$CONFIGS/anonymization_config_cve.json" \
        $CPU_FLAG \
        --results-dir "$OUT"

    # D3 — JSON — WITH anonymization config
    print_section "D3 JSON — WITH anonymization config (v3.0 | 4 strategies | 10 runs | ~14 min)"
    echo "  Input : $DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.json"
    echo "  Config: $CONFIGS/anonymization_config_cve.json"

    OUT="$RESULTS/D3_mock_cve_json__v3__all_strategies__10runs__with_config"
    mkdir -p "$OUT"
    run_cmd python3 "$BENCHMARK" \
        --benchmark \
        --file "$DATASETS/D3_mock_cais/cve_dataset_anonimizados_stratified.json" \
        --versions 3.0 \
        --strategies filtered hybrid standalone presidio \
        --runs 10 \
        --anonymization-config "$CONFIGS/anonymization_config_cve.json" \
        $CPU_FLAG \
        --results-dir "$OUT"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
print_section "COMPLETE"
echo ""
echo "  Results written to: $RESULTS/"
echo ""
echo "  Next step — run scientific analysis on all results:"
echo "    ./paper_data/scripts/analyze_all.sh"
echo ""
