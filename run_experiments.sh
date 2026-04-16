#!/usr/bin/env bash
# =============================================================================
# AnonShield — One-shot experiment reproducer for paper reviewers
# =============================================================================
#
# Runs the full OCR benchmark end-to-end and writes a consolidated report
# covering all 16 registered OCR engines × 9 preprocess configurations.
# Reviewers should only need to run:
#
#     ./run_experiments.sh                 # full matrix: 16 engines × 9 preprocess configs
#     ./run_experiments.sh --baseline      # all 16 engines, NO preprocessing (1 run per engine)
#     ./run_experiments.sh --smoke         # 2 samples, all 16 engines, 1 config (verifies setup)
#     ./run_experiments.sh --classical     # 8 classical engines × 9 preprocess configs
#     ./run_experiments.sh --vlm           # 8 VLM engines × 9 preprocess configs
#     ./run_experiments.sh --quick         # 20 samples, 4 classical engines, 1 config
#     ./run_experiments.sh --engines a,b   # custom engine list × 9 preprocess configs
#     ./run_experiments.sh --samples N     # override sample count (default 100)
#     ./run_experiments.sh --web           # also launch the web UI after the run
#     ./run_experiments.sh --help
#
# Engines (from src/anon/ocr/factory.py):
#   Classical (8): tesseract, easyocr, paddleocr, doctr, onnxtr, kerasocr, surya, rapidocr
#   VLM       (8): glm_ocr, paddle_vl, deepseek_ocr, monkey_ocr, lighton_ocr,
#                  chandra_ocr, dots_ocr, qwen_vl
#
# Preprocess configs (9):
#   grayscale, binarize, deskew, clahe, denoise, upscale, morph_open, border, preset_scan
#
# What it does:
#   1. Installs uv if missing, runs `uv sync`.
#   2. Auto-downloads the XFUND-pt dataset (first run only).
#   3. Runs every selected engine on every preprocess config (9 sub-runs, one
#      per config, each resumable independently).
#   4. Consolidates everything into benchmark/ocr/results/ablation_consolidated.csv.
#   5. Prints the ranked summary.
#
# Outputs:
#   benchmark/ocr/results/<config>/ocr_benchmark_summary.csv   (per config)
#   benchmark/ocr/results/ablation_consolidated.csv            (final table)
#   benchmark/ocr/results/experiment_run.log                   (full log)
#
# Notes for reviewers:
#   - Each configuration is independently resumable (per-doc keys in run_state.json).
#   - Engines whose dependencies are missing emit a message in the log and skip;
#     the run continues with the remaining engines.
#   - Some VLMs (glm_ocr, paddle_vl, lighton_ocr, deepseek_ocr) use transformers v5
#     and need a Docker image (see docker/ocr-vlm-v5.Dockerfile); they will report
#     is_available=False if run directly in the host env without that image.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[1;33m'; B=$'\033[0;34m'; N=$'\033[0m'
else
    R=""; G=""; Y=""; B=""; N=""
fi
info() { printf "${B}[experiments]${N} %s\n" "$*"; }
ok()   { printf "${G}[experiments]${N} %s\n" "$*"; }
warn() { printf "${Y}[experiments]${N} %s\n" "$*"; }
die()  { printf "${R}[experiments]${N} %s\n" "$*" >&2; exit 1; }

# ── Engine lists (sync with src/anon/ocr/factory.py) ────────────────────────
CLASSICAL="tesseract,easyocr,paddleocr,doctr,onnxtr,kerasocr,surya,rapidocr"
VLM="glm_ocr,paddle_vl,deepseek_ocr,monkey_ocr,lighton_ocr,chandra_ocr,dots_ocr,qwen_vl"
ALL="${CLASSICAL},${VLM}"

# ── Args ─────────────────────────────────────────────────────────────────────
MODE="all"
MAX_SAMPLES="100"
ENGINES="$ALL"
QUICK=0
BASELINE=0
START_WEB=0
i=1
while [[ $i -le $# ]]; do
    arg="${!i}"
    case "$arg" in
        --smoke)     MODE="smoke"; QUICK=1; MAX_SAMPLES="2";  ENGINES="$ALL" ;;
        --quick)     MODE="quick"; QUICK=1; MAX_SAMPLES="20"; ENGINES="tesseract,easyocr,doctr,rapidocr" ;;
        --baseline)  MODE="baseline"; BASELINE=1; ENGINES="$ALL" ;;
        --classical) MODE="classical"; ENGINES="$CLASSICAL" ;;
        --vlm)       MODE="vlm";       ENGINES="$VLM" ;;
        --all)       MODE="all";       ENGINES="$ALL" ;;
        --engines)   i=$((i+1)); MODE="custom"; ENGINES="${!i}" ;;
        --samples)   i=$((i+1)); MAX_SAMPLES="${!i}" ;;
        --web)       START_WEB=1 ;;
        -h|--help)   sed -n '3,50p' "$0"; exit 0 ;;
        *)           die "Unknown option: $arg  (see --help)" ;;
    esac
    i=$((i+1))
done

LOG="$SCRIPT_DIR/benchmark/ocr/results/experiment_run.log"
mkdir -p "$(dirname "$LOG")"

info "Mode: $MODE  |  samples: $MAX_SAMPLES"
info "Engines: $ENGINES"
info "Log: $LOG"

# ── 1. uv ────────────────────────────────────────────────────────────────────
if ! command -v uv >/dev/null 2>&1; then
    warn "uv not found — installing…"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
ok "uv: $(uv --version)"

# ── 2. Python environment ───────────────────────────────────────────────────
info "Syncing Python environment (uv sync — all OCR extras)…"
uv sync --extra ocr-all --extra paddle-ocr >>"$LOG" 2>&1 || die "uv sync failed — see $LOG"
ok "Environment ready"

# ── 3. System dependencies ──────────────────────────────────────────────────
if ! command -v tesseract >/dev/null 2>&1; then
    warn "tesseract not found — install with: sudo apt-get install -y tesseract-ocr tesseract-ocr-por"
fi

# ── 4. Run the benchmark ─────────────────────────────────────────────────────
export TORCH_DEVICE="${TORCH_DEVICE:-cuda}"
export ANON_SECRET_KEY="${ANON_SECRET_KEY:-$(openssl rand -hex 32)}"

run_cfg() {
    local name="$1" pre="$2"
    local out="$SCRIPT_DIR/benchmark/ocr/results/${name}"
    printf "\n${B}════ %s  (preprocess: %s) ════${N}\n" "$name" "${pre:-none}"
    local pre_flag=()
    [[ -n "$pre" ]] && pre_flag=(--preprocess "$pre")
    uv run python -m benchmark.ocr \
        --datasets xfund \
        --engines "$ENGINES" \
        --out-dir "$out" \
        --max-samples "$MAX_SAMPLES" \
        --store-texts \
        "${pre_flag[@]}" 2>&1 | tee -a "$LOG" || warn "Config $name had engine failures (continuing)"
}

info "─── Running $ENGINES on 9 preprocess configs ───"
if [[ "$BASELINE" -eq 1 ]]; then
    run_cfg none ""
elif [[ "$QUICK" -eq 1 ]]; then
    run_cfg grayscale "grayscale"
else
    run_cfg grayscale   "grayscale"
    run_cfg binarize    "grayscale,binarize"
    run_cfg deskew      "grayscale,deskew"
    run_cfg clahe       "grayscale,clahe"
    run_cfg denoise     "grayscale,denoise"
    run_cfg upscale     "upscale,grayscale"
    run_cfg morph_open  "grayscale,morph_open"
    run_cfg border      "grayscale,border"
    run_cfg preset_scan "grayscale,upscale,clahe,denoise,deskew,binarize,border"
fi
ok "Benchmark complete"

# ── 5. Consolidate ───────────────────────────────────────────────────────────
info "Consolidating results…"
uv run python -m benchmark.ocr.consolidate 2>&1 | tee -a "$LOG"
ok "Consolidated report: benchmark/ocr/results/ablation_consolidated.csv"

# ── 6. Summary ───────────────────────────────────────────────────────────────
echo
printf "${G}════════════════ Top 5 by CER (lower is better) ════════════════${N}\n"
if [[ -f benchmark/ocr/results/ablation_consolidated.csv ]]; then
    head -1 benchmark/ocr/results/ablation_consolidated.csv
    tail -n +2 benchmark/ocr/results/ablation_consolidated.csv | sort -t, -k4 -g | head -5
fi
echo
ok "Full report:       benchmark/ocr/REPORT.md"
ok "Methodology:       benchmark/ocr/METHODOLOGY.md"
ok "Per-engine audit:  benchmark/ocr/RESULTS_AUDIT.md"

# ── 7. Optional web UI ───────────────────────────────────────────────────────
if [[ "$START_WEB" -eq 1 ]]; then
    info "Starting web UI via docker compose…"
    command -v docker >/dev/null || die "docker not installed — skipping web UI"
    cd web
    docker compose -f docker-compose.dev.yml up --build -d
    ok "Web UI:  http://localhost:5173  (benchmark dashboard: /app/benchmark)"
    ok "API:     http://localhost:8000/api/docs"
    ok "Stop:    (cd web && docker compose -f docker-compose.dev.yml down)"
fi
