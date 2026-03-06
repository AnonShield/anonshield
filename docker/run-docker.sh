#!/bin/bash
# =============================================================================
# AnonLFI — Docker wrapper
#
# Creates an ./anon/ folder in your current directory to keep everything
# together: input files, output, and the NER model cache.
#
#   ./anon/
#   ├── input/    ← optional: put files here if you prefer
#   ├── output/   ← anonymized files appear here
#   ├── db/       ← entity mapping database (needed for de-anonymization)
#   └── models/   ← NER model cached here on first run (~1 GB, automatic)
#
# Usage:
#   export ANON_SECRET_KEY=$(openssl rand -hex 32)
#
#   ./run.sh ./YOUR_FILE.csv
#   ./run.sh ./your/folder/                     # entire folder
#   ./run.sh --gpu ./YOUR_FILE.csv              # GPU
#   ./run.sh --help
#   ./run.sh --list-entities
#
# Override the base folder:
#   ANON_DIR=./my-project/ ./run-docker.sh ./my-project/input/file.csv
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[anon]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[anon]${NC} $1"; }
log_error() { echo -e "${RED}[anon]${NC} $1"; }

# Portable absolute path resolver (works on Linux and macOS)
abs_path() {
    local p="$1"
    if [[ -d "$p" ]]; then
        (cd "$p" && pwd)
    else
        echo "$(cd "$(dirname "$p")" 2>/dev/null && pwd || pwd)/$(basename "$p")"
    fi
}

# ---------------------------------------------------------------------------
# Base directory — everything lives here
# ---------------------------------------------------------------------------
ANON_DIR="${ANON_DIR:-$(pwd)/anon}"
MODELS_DIR="$ANON_DIR/models"
DEFAULT_OUTPUT="$ANON_DIR/output"
DB_DIR="$ANON_DIR/db"

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
# Create folder structure
# ---------------------------------------------------------------------------
mkdir -p "$MODELS_DIR" "$DEFAULT_OUTPUT" "$ANON_DIR/input" "$DB_DIR"

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
VOLUMES=(-v "$MODELS_DIR":/app/models -v "$DB_DIR":/app/db)
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

        --word-list)
            i=$((i+1))
            val="${ARGS[$i]}"
            host=$(abs_path "$val")
            VOLUMES+=(-v "$(dirname "$host")":/anon_wordlist:ro)
            NEW_ARGS+=(--word-list /anon_wordlist/"$(basename "$host")")
            ;;

        --word-list=*)
            val="${arg#--word-list=}"
            host=$(abs_path "$val")
            VOLUMES+=(-v "$(dirname "$host")":/anon_wordlist:ro)
            NEW_ARGS+=(--word-list=/anon_wordlist/"$(basename "$host")")
            ;;

        --*)
            NEW_ARGS+=("$arg")
            # If next arg exists and doesn't start with --, it's the flag's value
            next_i=$((i+1))
            if [[ $next_i -lt ${#ARGS[@]} && "${ARGS[$next_i]}" != --* ]]; then
                i=$next_i
                NEW_ARGS+=("${ARGS[$i]}")
            fi
            ;;

        *)
            # First positional argument = input path
            if [[ $INPUT_SET -eq 0 ]]; then
                INPUT_SET=1
                host=$(abs_path "$arg")
                if [[ ! -e "$host" ]]; then
                    log_error "Input not found: $arg"
                    exit 1
                fi
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

# Default output: ./anon/output/
if [[ $OUTPUT_SET -eq 0 ]]; then
    OUTPUT_HOST="$DEFAULT_OUTPUT"
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
