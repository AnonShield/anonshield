#!/bin/bash
# =============================================================================
# AnonShield Docker Entrypoint - Lazy Loading Implementation
# =============================================================================
#
# This script implements lazy loading of ML models based on runtime arguments.
# Models are only downloaded when the user invokes a feature that requires them.
#
# Environment Variables:
#   ANON_LAZY_LOADING  - Enable lazy loading (default: 1)
#   ANON_PRELOAD       - Comma-separated list of models to preload
#   ANON_SECRET_KEY    - Secret key for anonymization
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[anon]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[anon]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[anon]${NC} $1"
}

log_error() {
    echo -e "${RED}[anon]${NC} $1"
}

# =============================================================================
# Feature Detection Functions
# =============================================================================

needs_spacy_model() {
    # spaCy is needed for all NER operations
    # Check if we're doing any anonymization or NER
    local args="$*"

    # If just --help, --list-entities, etc., no models needed
    if [[ "$args" == *"--help"* ]] || [[ "$args" == *"--list-entities"* ]] || [[ "$args" == *"--list-languages"* ]]; then
        return 1
    fi

    # Regex-only anonymization runs without NLP models
    if [[ "$args" =~ --anonymization-strategy[=\ ]regex ]] && [[ "$args" != *"--generate-ner-data"* ]]; then
        return 1
    fi

    # If there's a file path argument, we need NER models
    for arg in "$@"; do
        if [[ -f "$arg" ]] || [[ -d "$arg" ]]; then
            return 0
        fi
    done

    return 1
}

needs_transformer_model() {
    local args="$*"

    # Not needed for regex-only mode, nor for NER data generation (which runs
    # on the spaCy pipeline)
    if [[ "$args" =~ --anonymization-strategy[=\ ]regex ]] || [[ "$args" == *"--generate-ner-data"* ]]; then
        return 1
    fi

    # Not needed for help/info commands
    if [[ "$args" == *"--help"* ]] || [[ "$args" == *"--list-"* ]]; then
        return 1
    fi

    # Needed if processing files
    for arg in "$@"; do
        if [[ -f "$arg" ]] || [[ -d "$arg" ]]; then
            return 0
        fi
    done

    return 1
}

get_transformer_model() {
    local args="$*"
    local model="Davlan/xlm-roberta-base-ner-hrl"

    if [[ "$args" =~ --transformer-model[=\ ]([^ ]+) ]]; then
        model="${BASH_REMATCH[1]}"
    fi

    echo "$model"
}

get_language() {
    local args="$*"
    local lang="en"

    # Extract --lang argument
    if [[ "$args" =~ --lang[=\ ]([a-z]{2}) ]]; then
        lang="${BASH_REMATCH[1]}"
    fi

    echo "$lang"
}

# =============================================================================
# Model Provisioning Functions
# =============================================================================

ensure_spacy_model() {
    local model="$1"
    local venv_python="/app/.venv/bin/python"

    log_info "Checking spaCy model: $model"

    # Check if model is available
    if $venv_python -c "import spacy.util; exit(0 if spacy.util.is_package('$model') else 1)" 2>/dev/null; then
        log_success "spaCy model '$model' is available"
        return 0
    fi

    log_warn "spaCy model '$model' not found. Downloading..."

    if $venv_python -m spacy download "$model"; then
        log_success "spaCy model '$model' downloaded successfully"
        return 0
    else
        log_error "Failed to download spaCy model '$model'"
        return 1
    fi
}

ensure_transformer_model() {
    local model="$1"

    log_info "Checking transformer model: $model"

    # The model goes to the Hugging Face cache (HF_HOME=/app/models/huggingface,
    # on the models volume), which is where transformers loads it from. It used
    # to go to /app/models/<id>, which nothing read, so every run downloaded it
    # again into the container's throwaway home.
    # Cached = config plus weights present (the download skips formats that are
    # not needed, so the snapshot is not "complete" by huggingface_hub's measure).
    if ANON_MODEL="$model" /app/.venv/bin/python -c "
import os, sys
from huggingface_hub import try_to_load_from_cache
repo = os.environ['ANON_MODEL']
cached = lambda f: isinstance(try_to_load_from_cache(repo, f), str)
weights = ('model.safetensors', 'model.safetensors.index.json', 'pytorch_model.bin', 'pytorch_model.bin.index.json')
sys.exit(0 if cached('config.json') and any(cached(w) for w in weights) else 1)
" >/dev/null 2>&1; then
        log_success "Transformer model '$model' is available"
        return 0
    fi

    log_warn "Transformer model '$model' not found. Downloading..."

    # Only the PyTorch weights are fetched, and only the safetensors copy when
    # the repo has one (transformers loads that; many repos also carry a .bin).
    if ANON_MODEL="$model" /app/.venv/bin/python -c "
import os
from huggingface_hub import list_repo_files, snapshot_download
repo = os.environ['ANON_MODEL']
ignore = ['*.h5', '*.msgpack', '*.onnx', '*.ot', 'onnx/*', 'flax_model*', 'tf_model*', 'rust_model*']
if any(f.endswith('.safetensors') for f in list_repo_files(repo)):
    ignore += ['*.bin', '*.pt', '*.pth']
snapshot_download(repo_id=repo, max_workers=4, ignore_patterns=ignore)
print('Download complete')
"; then
        log_success "Transformer model '$model' downloaded successfully"
        return 0
    else
        log_error "Failed to download transformer model '$model'"
        return 1
    fi
}

# =============================================================================
# Preload Handler (for ANON_PRELOAD environment variable)
# =============================================================================

handle_preload() {
    if [[ -z "$ANON_PRELOAD" ]]; then
        return 0
    fi

    log_info "Preloading models: $ANON_PRELOAD"

    IFS=',' read -ra MODELS <<< "$ANON_PRELOAD"
    for model in "${MODELS[@]}"; do
        model=$(echo "$model" | xargs)  # trim whitespace
        case "$model" in
            spacy:*)
                ensure_spacy_model "${model#spacy:}"
                ;;
            transformer:*) 
                ensure_transformer_model "${model#transformer:}"
                ;;
            en_core_web_lg|pt_core_news_lg|*_core_*)
                ensure_spacy_model "$model"
                ;;
            *)
                log_warn "Unknown model format: $model"
                ;;
        esac
    done
}

# =============================================================================
# Main Entrypoint Logic
# =============================================================================

main() {
    log_info "AnonShield Container Starting..."

    # Handle preload if specified
    handle_preload

    # Skip lazy loading if disabled
    if [[ "${ANON_LAZY_LOADING:-1}" != "1" ]]; then
        log_info "Lazy loading disabled, running directly"
        exec /app/.venv/bin/python anon.py "$@"
    fi

    # Determine required models based on arguments. The engine loads
    # pt_core_news_lg for Portuguese and en_core_web_lg for every other
    # language; both ship in the image.
    local lang=$(get_language "$@")
    local spacy_model="en_core_web_lg"
    [[ "$lang" == "pt" ]] && spacy_model="pt_core_news_lg"

    # Provision models as needed
    if needs_spacy_model "$@"; then
        ensure_spacy_model "$spacy_model" || exit 1
    fi

    if needs_transformer_model "$@"; then
        ensure_transformer_model "$(get_transformer_model "$@")" || exit 1
        # The model is in the cache now: load it without asking the Hub for
        # updates, so a run makes no network call (and none fails offline).
        export HF_HUB_OFFLINE=1
    fi

    # Check if we should run unit tests instead of anon.py
    if [[ "$RUN_UNIT_TESTS" == "1" ]]; then
        log_info "Running unit tests..."
        export PATH="/app/.venv/bin:$PATH"
        export VIRTUAL_ENV="/app/.venv"
        python -m unittest discover -v -s tests/
    else
        log_success "All required models ready. Starting AnonShield..."
        exec /app/.venv/bin/python anon.py "$@"
    fi
}

# Run main with all arguments
main "$@"
