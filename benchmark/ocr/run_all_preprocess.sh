#!/usr/bin/env bash
set -u
LOG=/tmp/bench_chain.log
ROOT=/home/kapelinski/Documents/tool
BASE="uv run python3 -m benchmark.ocr --datasets xfund --engines tesseract,easyocr,doctr,surya,rapidocr --max-samples 100 --store-texts"
CONSOLIDATE="uv run python3 -m benchmark.ocr.consolidate"

cd "$ROOT" || exit 1

wait_for_pid() {
    local pid=$1
    while kill -0 "$pid" 2>/dev/null; do sleep 30; done
}

run_step() {
    local step=$1
    local name="${step:-baseline}"
    local dir="benchmark/ocr/results/${name}"
    local flag=""
    [ -n "$step" ] && flag="--preprocess $step"
    echo "[$(date '+%H:%M:%S')] === START: ${name} ===" >>"$LOG"
    $BASE --out-dir "$dir" $flag >>"$LOG" 2>&1
    echo "[$(date '+%H:%M:%S')] === END: ${name} ===" >>"$LOG"
}

CURRENT_PID=$(pgrep -f "benchmark.ocr --datasets xfund --engines tesseract,easyocr,doctr,surya,rapidocr --out-dir benchmark/ocr/results/grayscale" | head -1)
if [ -n "$CURRENT_PID" ]; then
    echo "[$(date '+%H:%M:%S')] Waiting for grayscale PID=$CURRENT_PID" >>"$LOG"
    wait_for_pid "$CURRENT_PID"
fi

for step in binarize deskew clahe denoise upscale morph_open border ""; do
    run_step "$step"
done

echo "[$(date '+%H:%M:%S')] === CONSOLIDATE ===" >>"$LOG"
$CONSOLIDATE >>"$LOG" 2>&1
echo "[$(date '+%H:%M:%S')] === DONE ===" >>"$LOG"
