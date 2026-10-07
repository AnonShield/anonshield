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
import json, os, sys
from pathlib import Path
from huggingface_hub import try_to_load_from_cache
repo = os.environ['ANON_MODEL']
cached = lambda f: isinstance(try_to_load_from_cache(repo, f), str)
weights = ('model.safetensors', 'model.safetensors.index.json', 'pytorch_model.bin', 'pytorch_model.bin.index.json')
complete_weights = False
for name in weights:
    path = try_to_load_from_cache(repo, name)
    if not isinstance(path, str):
        continue
    if name.endswith('.index.json'):
        shards = json.loads(Path(path).read_text()).get('weight_map', {}).values()
        complete_weights = bool(shards) and all(cached(shard) for shard in shards)
    else:
        complete_weights = True
    if complete_weights:
        break
tokenizer = any(cached(name) for name in ('tokenizer.json', 'sentencepiece.bpe.model', 'spiece.model', 'vocab.txt'))
sys.exit(0 if cached('config.json') and tokenizer and complete_weights else 1)
" >/dev/null 2>&1; then
        log_success "Transformer model '$model' is available"
        return 0
    fi

    log_warn "Transformer model '$model' not found. Downloading..."

    # Only the PyTorch weights are fetched, and only the safetensors copy when
    # the repo has one (transformers loads that; many repos also carry a .bin).
    # HF_HUB_VERBOSITY=error: without a token the Hub answers with a warning
    # header ("You are sending unauthenticated requests...") that the hub
    # client prints; no token is needed for public models.
    if ANON_MODEL="$model" HF_HUB_VERBOSITY=error /app/.venv/bin/python -c "
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
        log_error "Could not download '$model'. Check your connection and model name, then retry. The cache is kept. Use --anonymization-strategy regex to process without an NER model."
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

    # When run as a non-root user (run.sh passes --user on Linux), HOME is still
    # /root and not writable; libraries that cache under ~ need one.
    if [[ ! -w "${HOME:-/}" ]]; then
        export HOME=/tmp
    fi

    # Handle preload if specified
    handle_preload

    # Skip lazy loading if disabled
    if [[ "${ANON_LAZY_LOADING:-1}" != "1" ]]; then
        log_info "Lazy loading disabled, running directly"
        exec /app/.venv/bin/python anon.py "$@"
    fi

    if [[ $# -eq 0 ]]; then set -- --help; fi
    for arg in "$@"; do
        case "$arg" in
            -h|--help|--list-entities|--list-languages)
                exec /app/.venv/bin/python anon.py "$@" ;;
        esac
    done

    # Use the CLI's resolved configuration before downloading anything.
    local resolved
    resolved=$(/app/.venv/bin/python - "$@" <<'PYTHON'
import os
import sys
from anon import _parse_arguments
from src.anon.config import SECRET_KEY
try:
    args = _parse_arguments()
except (TypeError, ValueError) as exc:
    sys.exit(f"Invalid configuration: {exc}")
if not os.path.exists(args.file_path):
    sys.exit(f"Input not found: {args.file_path}")
if not args.generate_ner_data and args.slug_length != 0 and not SECRET_KEY:
    sys.exit("Set ANON_SECRET_KEY, use docker/run.sh to create one, or use --slug-length 0 for type-only labels.")
print(args.anonymization_strategy)
print(args.lang)
print(args.transformer_model)
print(int(args.generate_ner_data))
PYTHON
    ) || exit $?
    local settings
    mapfile -t settings <<< "$resolved"
    local strategy="${settings[0]}" lang="${settings[1]}" model="${settings[2]}" ner="${settings[3]}"
    local spacy_model="en_core_web_lg"
    [[ "$lang" == "pt" ]] && spacy_model="pt_core_news_lg"

    if [[ "$strategy" != "regex" || "$ner" == "1" ]]; then
        ensure_spacy_model "$spacy_model" || exit 1
    fi
    if [[ "$strategy" != "regex" && "$ner" != "1" ]]; then
        ensure_transformer_model "$model" || exit 1
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
