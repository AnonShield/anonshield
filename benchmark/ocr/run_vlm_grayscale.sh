#!/usr/bin/env bash
# VLM benchmarks on grayscale only (lower per-doc cost than full ablation).
# Runs sequentially, one engine at a time. Resumable via --out-dir.
set -u
LOG=/tmp/bench_vlm.log
ROOT=/home/kapelinski/Documents/tool

cd "$ROOT" || exit 1

run_engine() {
    local engine=$1
    local dir="benchmark/ocr/results/grayscale_vlm_${engine}"
    echo "[$(date '+%H:%M:%S')] === START VLM: ${engine} ===" >>"$LOG"
    uv run python3 -m benchmark.ocr \
        --datasets xfund \
        --engines "$engine" \
        --out-dir "$dir" \
        --max-samples 100 \
        --store-texts \
        --preprocess grayscale >>"$LOG" 2>&1
    echo "[$(date '+%H:%M:%S')] === END VLM: ${engine} ===" >>"$LOG"
}

# Wait for classical chain to finish (PID from run_all_preprocess.sh)
CHAIN_PID=$(pgrep -f "benchmark/ocr/run_all_preprocess.sh" | head -1)
if [ -n "$CHAIN_PID" ]; then
    echo "[$(date '+%H:%M:%S')] Waiting for classical chain PID=$CHAIN_PID" >>"$LOG"
    while kill -0 "$CHAIN_PID" 2>/dev/null; do sleep 60; done
fi

# Disk-constrained order: smallest first, delete HF cache between large ones
# glm_ocr (9B), chandra_ocr (9B), deepseek_ocr (3B, ~10GB cache), qwen_vl (7B)
# are all blocked on the 7.5 GB `/` partition — skip until TRANSFORMERS_CACHE
# is relocated (see docs/developers/OCR_ROADMAP.md "Plan" section).
for engine in paddle_vl lighton_ocr monkey_ocr; do
    run_engine "$engine"
done

echo "[$(date '+%H:%M:%S')] === VLM DONE ===" >>"$LOG"
