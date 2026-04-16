#!/usr/bin/env bash
# Post-chain queue: BID classical sweep → then VLM grayscale (paddle_vl first).
# Runs serially to avoid GPU contention. Each step resumable.
set -u
LOG=/tmp/bench_post_chain.log
ROOT=/home/kapelinski/Documents/tool

cd "$ROOT" || exit 1

# ── 1. Wait for XFUND preprocess chain ─────────────────────────────────────
CHAIN_PID=$(pgrep -f "benchmark/ocr/run_all_preprocess.sh" | head -1)
if [ -n "$CHAIN_PID" ]; then
    echo "[$(date '+%H:%M:%S')] Post-chain queue waiting for chain PID=$CHAIN_PID" >>"$LOG"
    while kill -0 "$CHAIN_PID" 2>/dev/null; do sleep 60; done
fi

# ── 2. BID classical sweep ─────────────────────────────────────────────────
echo "[$(date '+%H:%M:%S')] === START BID grayscale (5 classical engines) ===" >>"$LOG"
uv run python3 -m benchmark.ocr \
    --datasets bid \
    --engines tesseract,easyocr,doctr,surya,rapidocr \
    --out-dir benchmark/ocr/results/bid_grayscale \
    --store-texts \
    --preprocess grayscale >>"$LOG" 2>&1
echo "[$(date '+%H:%M:%S')] === END BID grayscale ===" >>"$LOG"

# ── 2b. PaddleOCR v5 on XFUND — install-gated (requires paddlepaddle) ──────
if uv run python3 -c "from paddleocr import PaddleOCR" 2>/dev/null; then
    echo "[$(date '+%H:%M:%S')] === START paddleocr grayscale (v5) ===" >>"$LOG"
    uv run python3 -m benchmark.ocr \
        --datasets xfund \
        --engines paddleocr \
        --out-dir benchmark/ocr/results/grayscale_paddleocr \
        --max-samples 100 \
        --store-texts \
        --preprocess grayscale >>"$LOG" 2>&1
    echo "[$(date '+%H:%M:%S')] === END paddleocr ===" >>"$LOG"
else
    echo "[$(date '+%H:%M:%S')] paddleocr not installed — skipping" >>"$LOG"
fi

# ── 3. VLM sweep (disk-fitted: paddle_vl, lighton_ocr, monkey_ocr) ─────────
for engine in paddle_vl lighton_ocr monkey_ocr; do
    dir="benchmark/ocr/results/grayscale_vlm_${engine}"
    echo "[$(date '+%H:%M:%S')] === START VLM: ${engine} ===" >>"$LOG"
    uv run python3 -m benchmark.ocr \
        --datasets xfund \
        --engines "$engine" \
        --out-dir "$dir" \
        --max-samples 100 \
        --store-texts \
        --preprocess grayscale >>"$LOG" 2>&1
    echo "[$(date '+%H:%M:%S')] === END VLM: ${engine} ===" >>"$LOG"
done

echo "[$(date '+%H:%M:%S')] === POST-CHAIN DONE ===" >>"$LOG"
