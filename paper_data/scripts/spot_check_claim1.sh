#!/bin/bash
# =============================================================================
# spot_check_claim1.sh — Claim #1 verification: v2.0 vs AnonShield speedup ratio
# on a ~512 KB subset of D3 CSV. The ratio is hardware-independent; only
# absolute times vary by machine.
#
# Usage (from workspace root):
#   ./paper_data/scripts/spot_check_claim1.sh [--cpu-only]
#
# Runtime: ~8–15 min depending on hardware (dominated by v2.0 low throughput).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/../.." && pwd)"
BENCH="$WS/benchmark/benchmark.py"
D3="$WS/paper_data/datasets/D3_mock_cais/cve_dataset_anonimizados_stratified.csv"
D3_KB=253391    # full D3 CSV size in KB (247.45 MB)

CPU_ONLY=false
for a in "$@"; do [[ "$a" == "--cpu-only" ]] && CPU_ONLY=true; done
if [[ "$CPU_ONLY" == "true" ]]; then
    export CUDA_VISIBLE_DEVICES=""
    CPU_FLAG="--cpu-only"
else
    CPU_FLAG=""
fi

[[ -f "$D3" ]]    || { echo "ERROR: D3 not found. Run: ./paper_data/scripts/extract_datasets.sh"; exit 1; }
[[ -f "$BENCH" ]] || { echo "ERROR: benchmark.py not found at $BENCH"; exit 1; }

# ── Auto-setup v2.0 environment if not found ──────────────────────────────
if [[ ! -d "$WS/anonlfi_2.0/.venv" ]]; then
    echo "  AnonLFI v2.0 environment not found — running setup (required once)..."
    python3 "$BENCH" --setup --versions 1.0 2.0 3.0 $CPU_FLAG
    if [[ ! -d "$WS/anonlfi_2.0/.venv" ]]; then
        echo "  ERROR: v2.0 setup failed. Check output above."
        exit 1
    fi
fi

WORK=$(mktemp -d)
SUB="$WORK/sub.csv"
trap 'rm -rf "$WORK"' EXIT

# ── Create ~512 KB subset ─────────────────────────────────────────────────
echo "Preparing ~512 KB subset of D3 CSV..."
python3 - "$D3" "$SUB" <<'PY'
import sys, os
src, dst = sys.argv[1], sys.argv[2]
target = 512 * 1024
total = 0
with open(src, encoding='utf-8') as fin, open(dst, 'w', encoding='utf-8') as fout:
    for line in fin:
        fout.write(line)
        total += len(line.encode('utf-8'))
        if total >= target:
            break
print(f"  {os.path.getsize(dst)/1024:.0f} KB")
PY

# ── Run benchmarks ────────────────────────────────────────────────────────
echo "Running v2.0  (est. ~8–10 min, varies by hardware)..."
python3 "$BENCH" --benchmark --file "$SUB" \
    --versions 2.0 --runs 1 $CPU_FLAG \
    --results-dir "$WORK/v2" > "$WORK/v2.log" 2>&1

echo "Running AnonShield standalone..."
python3 "$BENCH" --benchmark --file "$SUB" \
    --versions 3.0 --strategies standalone --runs 1 $CPU_FLAG \
    --results-dir "$WORK/v3" > "$WORK/v3.log" 2>&1

# ── Print results ─────────────────────────────────────────────────────────
python3 - "$WORK/v2/benchmark_results.csv" "$WORK/v3/benchmark_results.csv" \
           "$SUB" "$D3_KB" <<'PY'
import csv, os, sys

def read_time(path):
    try:
        with open(path) as f:
            ok = [r for r in csv.DictReader(f) if r.get('status') == 'SUCCESS']
        return float(ok[0]['wall_clock_time_sec']) if ok else None
    except FileNotFoundError:
        return None

v2f, v3f, sub, full_kb = sys.argv[1:]
t2, t3 = read_time(v2f), read_time(v3f)
full_kb = float(full_kb)

if not t2 or not t3:
    print("ERROR: one or more benchmark runs failed.")
    print("       Check logs for details.")
    sys.exit(1)

sub_kb = os.path.getsize(sub) / 1024
tp2    = sub_kb / t2           # KB/s — v2.0 throughput on this machine
tp3    = sub_kb / t3           # KB/s — AnonShield throughput on this machine
est2_h = full_kb / tp2 / 3600  # v2.0 extrapolated to full D3 (lower bound — from measured throughput)
est3_s = full_kb / tp3         # AnonShield extrapolated to full D3 (upper bound — cache improves)

print()
print("══════════════════════════════════════════════════════════════")
print(f"  Claim #1 Spot Check  ({sub_kb:.0f} KB subset of D3 CSV)")
print("══════════════════════════════════════════════════════════════")
print(f"  v2.0  default    : {t2:>8.1f} s   ({tp2:.2f} KB/s on this machine)")
print(f"  AnonShield  standalone : {t3:>8.1f} s   ({tp3:.0f} KB/s on this machine)")
print(f"  Speedup          : {t2/t3:.0f}×  (varies by hardware — larger when GPU is available)")
print()
print(f"  Extrapolating to full D3 (247 MB) via measured throughputs:")
print(f"  v2.0 on full D3  : ≥ {est2_h:.1f} h   (lower bound — extrapolated from measured throughput)")
print(f"  AnonShield on full D3  : ≤ {est3_s:.0f} s   (upper bound — AnonShield cache improves at scale)")
print(f"  Projected speedup: ≥ {est2_h*3600/est3_s:.0f}×")
print("══════════════════════════════════════════════════════════════")
PY
