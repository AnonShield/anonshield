#!/bin/bash
# =============================================================================
# spot_check_claim3.sh — Claim #3 verification: anonymization_config speedup
# on D3 CSV (full dataset, v3.0 standalone).
#
# Runs v3.0 standalone twice on the full D3 CSV: once without config
# (~73 s GPU / ~434 s CPU) and once with config (~8 s GPU / ~9 s CPU).
# Prints measured times and config speedup ratio.
#
# Usage (from workspace root):
#   ./paper_data/scripts/spot_check_claim3.sh [--cpu-only]
#
# Runtime: ~80 s GPU / ~450 s CPU (~1.5–8 min)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/../.." && pwd)"
BENCH="$WS/benchmark/benchmark.py"
D3="$WS/paper_data/datasets/D3_mock_cais/cve_dataset_anonimizados_stratified.csv"
CFG="$WS/paper_data/configs/anonymization_config_cve.json"

CPU_ONLY=false
for a in "$@"; do [[ "$a" == "--cpu-only" ]] && CPU_ONLY=true; done
if [[ "$CPU_ONLY" == "true" ]]; then
    export CUDA_VISIBLE_DEVICES=""
    CPU_FLAG="--cpu-only"
else
    CPU_FLAG=""
fi

[[ -f "$D3" ]]    || { echo "ERROR: D3 not found. Run: ./paper_data/scripts/download_datasets.sh"; exit 1; }
[[ -f "$BENCH" ]] || { echo "ERROR: benchmark.py not found at $BENCH"; exit 1; }
[[ -f "$CFG" ]]   || { echo "ERROR: config not found at $CFG"; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "Running v3.0 standalone WITHOUT config (est. ~73 s GPU / ~434 s CPU)..."
python3 "$BENCH" --benchmark --file "$D3" \
    --versions 3.0 --strategies standalone --runs 1 $CPU_FLAG \
    --results-dir "$WORK/without" > "$WORK/without.log" 2>&1

echo "Running v3.0 standalone WITH config (est. ~8 s GPU / ~9 s CPU)..."
python3 "$BENCH" --benchmark --file "$D3" \
    --versions 3.0 --strategies standalone --runs 1 $CPU_FLAG \
    --anonymization-config "$CFG" \
    --results-dir "$WORK/with" > "$WORK/with.log" 2>&1

# ── Print results ─────────────────────────────────────────────────────────────
python3 - "$WORK/without/benchmark_results.csv" "$WORK/with/benchmark_results.csv" <<'PY'
import csv, sys

def read_time(path):
    try:
        with open(path) as f:
            ok = [r for r in csv.DictReader(f) if r.get('status') == 'SUCCESS']
        return float(ok[0]['wall_clock_time_sec']) if ok else None
    except FileNotFoundError:
        return None

t_no, t_with = read_time(sys.argv[1]), read_time(sys.argv[2])

if not t_no or not t_with:
    print("ERROR: one or more benchmark runs failed.")
    print("       Check logs for details.")
    sys.exit(1)

print()
print("══════════════════════════════════════════════════════════════")
print("  Claim #3 Spot Check  (D3 CSV, v3.0 standalone)")
print("══════════════════════════════════════════════════════════════")
print(f"  without config  : {t_no:>8.1f} s")
print(f"  with config     : {t_with:>8.1f} s")
print(f"  Config speedup  : {t_no/t_with:.1f}×")
print()
print("  Note: with config, GPU and CPU times converge to ~8–9 s each,")
print("  because no field passes through the NER or regex pipeline.")
print("  The CPU gain is therefore larger than the GPU gain (~50× vs ~9×).")
print("══════════════════════════════════════════════════════════════")
PY
