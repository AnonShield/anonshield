#!/bin/bash
# =============================================================================
# AnonLFI — Docker Hub wrapper
#
# Run from the directory containing your ./data/ folder.
# Input files go in ./data/input/, output lands in ./data/output/.
#
# Usage:
#   chmod +x run-docker.sh
#   export ANON_SECRET_KEY="your-secret-key"
#
#   ./run-docker.sh /data/input/YOUR_FILE.csv
#   ./run-docker.sh /data/input/                    # process entire directory
#   ./run-docker.sh --gpu /data/input/YOUR_FILE.csv # GPU
#   ./run-docker.sh --help
#   ./run-docker.sh --list-entities
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[anon]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[anon]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[anon]${NC} $1"; }
log_error() { echo -e "${RED}[anon]${NC} $1"; }

# ---------------------------------------------------------------------------
# Parse --gpu (consumed here, not forwarded to anon.py)
# ---------------------------------------------------------------------------
USE_GPU=0
ARGS=()
for arg in "$@"; do
    [[ "$arg" == "--gpu" ]] && USE_GPU=1 || ARGS+=("$arg")
done

# ---------------------------------------------------------------------------
# Detect info-only commands (no key or output-dir needed)
# ---------------------------------------------------------------------------
IS_INFO_CMD=0
HAS_OUTPUT_DIR=0
for arg in "${ARGS[@]:-}"; do
    [[ "$arg" == "--help" || "$arg" == --list-* ]] && IS_INFO_CMD=1
    [[ "$arg" == "--output-dir" ]] && HAS_OUTPUT_DIR=1
done

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
if ! docker info &>/dev/null; then
    log_error "Docker is not running."
    exit 1
fi

if [[ -z "${ANON_SECRET_KEY:-}" && $IS_INFO_CMD -eq 0 ]]; then
    log_error "ANON_SECRET_KEY is not set."
    log_error "Generate one:  export ANON_SECRET_KEY=\$(openssl rand -hex 32)"
    exit 1
fi

# ---------------------------------------------------------------------------
# Create local directories
# ---------------------------------------------------------------------------
mkdir -p ./data/input ./data/output ./data/models

# ---------------------------------------------------------------------------
# Select image
# ---------------------------------------------------------------------------
if [[ $USE_GPU -eq 1 ]]; then
    IMAGE="anonshield/anon:gpu"
    GPU_FLAGS=(--gpus all)
    log_info "Using GPU image"
else
    IMAGE="anonshield/anon:latest"
    GPU_FLAGS=()
fi

# ---------------------------------------------------------------------------
# Build extra args
# ---------------------------------------------------------------------------
EXTRA=()
if [[ $IS_INFO_CMD -eq 0 && $HAS_OUTPUT_DIR -eq 0 ]]; then
    EXTRA+=(--output-dir /data/output/)
fi

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
docker run --rm \
    "${GPU_FLAGS[@]}" \
    -e ANON_SECRET_KEY="${ANON_SECRET_KEY:-}" \
    -v "$(pwd)/data":/data \
    -v "$(pwd)/data/models":/app/models \
    "$IMAGE" \
    "${ARGS[@]}" \
    "${EXTRA[@]}"

if [[ $IS_INFO_CMD -eq 0 ]]; then
    log_ok "Output is in ./data/output/"
fi
