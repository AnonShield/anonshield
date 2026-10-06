#!/bin/bash
# =============================================================================
# AnonShield — Docker wrapper
#
# Creates an ./anon/ folder in your current directory to keep everything
# together: input files, output, and the NER model cache.
#
#   ./anon/
#   ├── input/    ← optional: put files here if you prefer
#   ├── output/   ← anonymized files appear here
#   ├── db/       ← entity mapping database (needed for de-anonymization)
#   ├── models/   ← NER model cached here on first run (~1 GB, automatic)
#   └── secret.key ← HMAC key, created on the first run (unless ANON_SECRET_KEY is set)
#
# Usage:
#   ./run.sh ./YOUR_FILE.csv
#   ./run.sh ./your/folder/                     # entire folder
#   ./run.sh --gpu ./YOUR_FILE.csv              # GPU
#   ./run.sh --help
#   ./run.sh --list-entities
#
# Override the base folder:
#   ANON_DIR=./my-project/ ./run.sh ./my-project/input/file.csv
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
KEY_FILE="$ANON_DIR/secret.key"

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
SLUG_ZERO=0
prev=""
for arg in "${ARGS[@]:-}"; do
    [[ "$arg" == "--help" || "$arg" == --list-* ]] && IS_INFO_CMD=1
    [[ "$arg" == "--slug-length=0" || ( "$prev" == "--slug-length" && "$arg" == "0" ) ]] && SLUG_ZERO=1
    prev="$arg"
done

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    log_error "Docker is not installed: https://docs.docker.com/get-docker/"
    exit 1
fi
if ! docker_err=$(docker info 2>&1 >/dev/null); then
    if [[ "$docker_err" == *"permission denied"* ]]; then
        log_error "This user cannot use Docker. Add it to the docker group, then log out and back in:"
        log_error "  sudo usermod -aG docker \$USER"
    else
        log_error "Docker is not running. Start it and try again."
        log_error "($(echo "$docker_err" | tail -n 1))"
    fi
    exit 1
fi

# ---------------------------------------------------------------------------
# Create folder structure
# ---------------------------------------------------------------------------
mkdir -p "$MODELS_DIR" "$DEFAULT_OUTPUT" "$ANON_DIR/input" "$DB_DIR"

# ---------------------------------------------------------------------------
# Secret key: ANON_SECRET_KEY if set, otherwise the one kept in
# ./anon/secret.key, created on the first run. The same key gives the same
# pseudonyms across runs. --slug-length 0 (type-only labels) needs none.
# ---------------------------------------------------------------------------
if [[ -z "${ANON_SECRET_KEY:-}" && $IS_INFO_CMD -eq 0 && $SLUG_ZERO -eq 0 ]]; then
    if [[ ! -s "$KEY_FILE" ]]; then
        (umask 077; od -An -tx1 -N32 /dev/urandom | tr -d ' \n' > "$KEY_FILE")
        log_info "Created a secret key in $KEY_FILE; it keeps pseudonyms the same across runs."
        log_info "Keep it with $DB_DIR (or set ANON_SECRET_KEY to use your own key)."
    fi
    ANON_SECRET_KEY=$(tr -d ' \n' < "$KEY_FILE")
fi
# Handed to docker run by name (-e ANON_SECRET_KEY), so the key is not on its
# command line, which any local user can read with ps.
export ANON_SECRET_KEY="${ANON_SECRET_KEY:-}"

# ---------------------------------------------------------------------------
# Select image
# ---------------------------------------------------------------------------
# The GPU image comes in two PyTorch builds: :gpu (CUDA 13.0) needs NVIDIA
# driver 580+ and an RTX 20xx or newer (CUDA 13 dropped older GPUs; RTX 50xx
# needs it); :gpu-cu126 (CUDA 12.6) covers older GPUs and drivers.
# ANON_GPU_IMAGE overrides the choice.
pick_gpu_image() {
    local info cc drv cc_num drv_major
    info=$(nvidia-smi --query-gpu=compute_cap,driver_version --format=csv,noheader 2>/dev/null | head -n1 || true)
    cc=$(echo "$info" | cut -d, -f1 | tr -d ' ')
    drv=$(echo "$info" | cut -d, -f2 | tr -d ' ')
    if [[ ! "$cc" =~ ^[0-9]+\.[0-9]+$ || ! "$drv" =~ ^[0-9]+ ]]; then
        log_info "Could not read the GPU from nvidia-smi; using anonshield/anon:gpu" >&2
        echo "anonshield/anon:gpu"
        return
    fi
    cc_num=$(( ${cc%%.*} * 10 + ${cc##*.} ))
    drv_major=${drv%%.*}
    if (( cc_num >= 75 && drv_major >= 580 )); then
        echo "anonshield/anon:gpu"
    else
        if (( cc_num >= 100 )); then
            log_info "This GPU (compute capability $cc) needs NVIDIA driver 580+ for GPU inference; driver is $drv, it will run on CPU" >&2
        fi
        echo "anonshield/anon:gpu-cu126"
    fi
}

if [[ $USE_GPU -eq 1 ]]; then
    IMAGE="${ANON_GPU_IMAGE:-$(pick_gpu_image)}"
    GPU_FLAGS=(--gpus all)
    log_info "Using GPU image $IMAGE"
else
    IMAGE="anonshield/anon:latest"
    GPU_FLAGS=()
fi

# ---------------------------------------------------------------------------
# Run as the calling user on Linux. As root (the image default), the output,
# the database and the model cache came out owned by root: not editable or
# removable without sudo. Docker Desktop (macOS, Windows) maps ownership itself.
# ---------------------------------------------------------------------------
USER_FLAGS=()
if [[ "$(uname -s)" == "Linux" && "$(id -u)" -ne 0 ]]; then
    USER_FLAGS=(--user "$(id -u):$(id -g)")
    # An ./anon folder used by an older version of this script holds files
    # owned by root, which the container can no longer write as this user.
    if [[ -n "$(find "$ANON_DIR" ! -user "$(id -u)" -print -quit 2>/dev/null)" ]]; then
        log_info "Giving $ANON_DIR back to $(id -un) (an older version left root-owned files in it)"
        docker run --rm -v "$ANON_DIR":/anon_dir --entrypoint chown "$IMAGE" -R "$(id -u):$(id -g)" /anon_dir
    fi
fi

# ---------------------------------------------------------------------------
# Info commands: no path remapping needed
# ---------------------------------------------------------------------------
if [[ $IS_INFO_CMD -eq 1 ]]; then
    docker run --rm \
        ${USER_FLAGS[@]+"${USER_FLAGS[@]}"} \
        ${GPU_FLAGS[@]+"${GPU_FLAGS[@]}"} \
        -e ANON_SECRET_KEY \
        -v "$MODELS_DIR":/app/models \
        "$IMAGE" \
        ${ARGS[@]+"${ARGS[@]}"}
    exit 0
fi

# ---------------------------------------------------------------------------
# Remap local paths to container paths
#
# Each local path gets its own volume mount:
#   input file/dir  → /anon_input[/filename]
#   --output-dir    → /anon_output
#   --anonymization-config, --word-list, --custom-patterns, --config
#                   → /anon_files/<n>/filename
# ---------------------------------------------------------------------------
VOLUMES=(-v "$MODELS_DIR":/app/models -v "$DB_DIR":/app/db)
NEW_ARGS=()

# anon.py flags that take no value (store_true / store_false)
BOOL_FLAGS=" --help --list-entities --list-languages --overwrite --no-report \
 --preserve-row-context --optimize --use-cache --no-use-cache --skip-numeric \
 --regex-priority --disable-gc --force-large-xml --generate-ner-data --ner-include-all \
 --ner-aggregate-record --use-datasets "
is_bool_flag() { [[ "$BOOL_FLAGS" == *" $1 "* ]]; }

# Mount the directory of a file argument read-only and point the flag at it.
FILE_MOUNTS=0
mount_file_arg() {
    local flag="$1" val="$2" host mnt
    if [[ -z "$val" ]]; then
        log_error "$flag needs a file path."
        exit 1
    fi
    host=$(abs_path "$val")
    if [[ ! -f "$host" ]]; then
        log_error "File not found for $flag: $val"
        exit 1
    fi
    FILE_MOUNTS=$((FILE_MOUNTS+1))
    mnt="/anon_files/$FILE_MOUNTS"
    VOLUMES+=(-v "$(dirname "$host")":"$mnt":ro)
    NEW_ARGS+=("$flag" "$mnt/$(basename "$host")")
}
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

        --anonymization-config|--word-list|--custom-patterns|--config)
            i=$((i+1))
            mount_file_arg "$arg" "${ARGS[$i]:-}"
            ;;

        --anonymization-config=*|--word-list=*|--custom-patterns=*|--config=*)
            mount_file_arg "${arg%%=*}" "${arg#*=}"
            ;;

        --*=*)
            NEW_ARGS+=("$arg")
            ;;

        --*)
            NEW_ARGS+=("$arg")
            # Flags that take a value consume the next argument; boolean flags
            # do not (treating "--overwrite file.csv" as a flag and its value
            # used to swallow the input path).
            if ! is_bool_flag "$arg"; then
                next_i=$((i+1))
                if [[ $next_i -lt ${#ARGS[@]} ]]; then
                    i=$next_i
                    NEW_ARGS+=("${ARGS[$i]}")
                fi
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
# ${arr[@]+"${arr[@]}"}: an empty array is an "unbound variable" under set -u
# in bash < 4.4 (the macOS default).
docker run --rm \
    ${USER_FLAGS[@]+"${USER_FLAGS[@]}"} \
    ${GPU_FLAGS[@]+"${GPU_FLAGS[@]}"} \
    -e ANON_SECRET_KEY \
    "${VOLUMES[@]}" \
    "$IMAGE" \
    ${NEW_ARGS[@]+"${NEW_ARGS[@]}"}

log_ok "Output is in $OUTPUT_HOST"