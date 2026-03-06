#!/bin/bash
# =============================================================================
# AnonLFI — Docker wrapper
#
# Usage:
#   export ANON_SECRET_KEY=$(openssl rand -hex 32)
#
#   ./run-docker.sh /path/to/file.csv
#   ./run-docker.sh /path/to/file.csv --output-dir /path/to/results/
#   ./run-docker.sh /path/to/scans/                   # entire directory
#   ./run-docker.sh --gpu /path/to/file.csv           # GPU
#   ./run-docker.sh --help
#   ./run-docker.sh --list-entities
#
# Models are cached in ~/.cache/anonshield/models/ (shared across runs).
# Override with: export ANON_MODELS_DIR=/your/path
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[anon]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[anon]${NC} $1"; }
log_error() { echo -e "${RED}[anon]${NC} $1"; }

# Resolve a path to absolute (works on Linux and macOS, no realpath required)
abs_path() {
    local p="$1"
    if [[ -d "$p" ]]; then
        (cd "$p" && pwd)
    else
        echo "$(cd "$(dirname "$p")" 2>/dev/null && pwd || pwd)/$(basename "$p")"
    fi
}

# ---------------------------------------------------------------------------
# Parse --gpu (consumed here, not forwarded)
# ---------------------------------------------------------------------------
USE_GPU=0
ARGS=()
for arg in "$@"; do
    [[ "$arg" == "--gpu" ]] && USE_GPU=1 || ARGS+=("$arg")
done

# ---------------------------------------------------------------------------
# Detect info-only commands (no key needed, no path remapping)
# ---------------------------------------------------------------------------
IS_INFO_CMD=0
for arg in "${ARGS[@]:-}"; do
    [[ "$arg" == "--help" || "$arg" == --list-* ]] && IS_INFO_CMD=1
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
# Models cache (shared across all projects)
# ---------------------------------------------------------------------------
MODELS_DIR="${ANON_MODELS_DIR:-$HOME/.cache/anonshield/models}"
mkdir -p "$MODELS_DIR"

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
# Info commands: no path remapping needed
# ---------------------------------------------------------------------------
if [[ $IS_INFO_CMD -eq 1 ]]; then
    docker run --rm \
        "${GPU_FLAGS[@]}" \
        -e ANON_SECRET_KEY="${ANON_SECRET_KEY:-}" \
        -v "$MODELS_DIR":/app/models \
        "$IMAGE" \
        "${ARGS[@]}"
    exit 0
fi

# ---------------------------------------------------------------------------
# Remap local paths to container paths
#
# Each local path gets its own volume mount:
#   input file/dir  → /anon_input[/filename]
#   --output-dir    → /anon_output
#   --anonymization-config → /anon_config/filename
# ---------------------------------------------------------------------------
VOLUMES=(-v "$MODELS_DIR":/app/models)
NEW_ARGS=()
INPUT_SET=0
OUTPUT_SET=0
OUTPUT_HOST=""

i=0
while [[ $i -lt ${#ARGS[@]} ]]; do
    arg="${ARGS[$i]}"

    case "$arg" in

        --output-dir)
            i=$((i+1))
            val="${ARGS[$i]}"
            host=$(abs_path "$val")
            mkdir -p "$host"
            VOLUMES+=(-v "$host":/anon_output)
            NEW_ARGS+=(--output-dir /anon_output)
            OUTPUT_SET=1
            OUTPUT_HOST="$host"
            ;;

        --output-dir=*)
            val="${arg#--output-dir=}"
            host=$(abs_path "$val")
            mkdir -p "$host"
            VOLUMES+=(-v "$host":/anon_output)
            NEW_ARGS+=(--output-dir /anon_output)
            OUTPUT_SET=1
            OUTPUT_HOST="$host"
            ;;

        --anonymization-config)
            i=$((i+1))
            val="${ARGS[$i]}"
            host=$(abs_path "$val")
            VOLUMES+=(-v "$(dirname "$host")":/anon_config:ro)
            NEW_ARGS+=(--anonymization-config /anon_config/"$(basename "$host")")
            ;;

        --anonymization-config=*)
            val="${arg#--anonymization-config=}"
            host=$(abs_path "$val")
            VOLUMES+=(-v "$(dirname "$host")":/anon_config:ro)
            NEW_ARGS+=(--anonymization-config=/anon_config/"$(basename "$host")")
            ;;

        --*)
            # Any other flag: pass through unchanged
            NEW_ARGS+=("$arg")
            ;;

        *)
            # First positional argument = input path
            if [[ $INPUT_SET -eq 0 ]]; then
                INPUT_SET=1
                host=$(abs_path "$arg")
                if [[ -d "$host" ]]; then
                    VOLUMES+=(-v "$host":/anon_input:ro)
                    NEW_ARGS+=(/anon_input)
                else
                    VOLUMES+=(-v "$(dirname "$host")":/anon_input:ro)
                    NEW_ARGS+=(/anon_input/"$(basename "$host")")
                fi
            else
                NEW_ARGS+=("$arg")
            fi
            ;;
    esac

    i=$((i+1))
done

# Default output: ./output/ next to where the script is run
if [[ $OUTPUT_SET -eq 0 ]]; then
    OUTPUT_HOST="$(pwd)/output"
    mkdir -p "$OUTPUT_HOST"
    VOLUMES+=(-v "$OUTPUT_HOST":/anon_output)
    NEW_ARGS+=(--output-dir /anon_output)
fi

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
docker run --rm \
    "${GPU_FLAGS[@]}" \
    -e ANON_SECRET_KEY="${ANON_SECRET_KEY:-}" \
    "${VOLUMES[@]}" \
    "$IMAGE" \
    "${NEW_ARGS[@]}"

log_ok "Output is in $OUTPUT_HOST"
