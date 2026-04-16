#!/usr/bin/env bash
# OCR Benchmark — Preprocessing ablation sweep
#
# Runs every preprocessing configuration against every available engine.
# Each config writes to its own results dir and is independently resumable.
#
# Usage:  bash benchmark/ocr/run_ablation.sh [MAX_SAMPLES] [ENGINES]
#
# Examples:
#   bash benchmark/ocr/run_ablation.sh 100 tesseract,easyocr,doctr,surya,rapidocr
#   bash benchmark/ocr/run_ablation.sh 50

set -euo pipefail

MAX_SAMPLES="${1:-100}"
ENGINES="${2:-tesseract,easyocr,doctr,surya,rapidocr}"
DATASETS="xfund"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# Surya reads TORCH_DEVICE to pick its Predictor device (see surya.settings).
# Set it here so Surya uses CUDA when available; EasyOCR/DocTR use their own flags.
export TORCH_DEVICE="${TORCH_DEVICE:-cuda}"

run_cfg() {
    local name="$1" pre="$2"
    local out_dir="$SCRIPT_DIR/results/${name}"
    echo -e "\n════════════════════════════════════════════════════════════════"
    echo " [$(date '+%H:%M:%S')] ${name}  (preprocess: ${pre:-none})"
    echo "════════════════════════════════════════════════════════════════"

    local pre_args=()
    [[ -n "$pre" ]] && pre_args=(--preprocess "$pre")

    uv run python3 -m benchmark.ocr \
        --datasets "$DATASETS" \
        --engines "$ENGINES" \
        --out-dir "$out_dir" \
        --max-samples "$MAX_SAMPLES" \
        --store-texts \
        "${pre_args[@]}" || { echo "FAILED: ${name}"; return 1; }

    echo " [DONE] ${name}"
}

# baseline is already populated by the caller; ablation runs only.
run_cfg "grayscale"            "grayscale"
run_cfg "binarize"             "grayscale,binarize"
run_cfg "deskew"               "grayscale,deskew"
run_cfg "clahe"                "grayscale,clahe"
run_cfg "denoise"              "grayscale,denoise"
run_cfg "upscale"              "upscale,grayscale"
run_cfg "preset_scan"          "grayscale,upscale,clahe,denoise,deskew,binarize,border"
run_cfg "minimal"              "grayscale,clahe,binarize"

echo -e "\nAll ablation configs done. Results under $SCRIPT_DIR/results/"
