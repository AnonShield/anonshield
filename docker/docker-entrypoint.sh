#!/bin/bash
# =============================================================================
# AnonLFI Docker Entrypoint - Lazy Loading Implementation
# =============================================================================
#
# This script implements lazy loading of ML models based on runtime arguments.
# Models are only downloaded when the user invokes a feature that requires them.
#
# Environment Variables:
#   ANON_LAZY_LOADING  - Enable lazy loading (default: 1)
#   ANON_PRELOAD       - Comma-separated list of models to preload
#   OLLAMA_BASE_URL    - Ollama service URL (default: http://ollama:11434)
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
    # spaCy is needed for all NER operations (unless --slm-only mode in future)
    # Check if we're doing any anonymization or NER
    local args="$*"

    # If just --help, --list-entities, etc., no models needed
    if [[ "$args" == *"--help"* ]] || [[ "$args" == *"--list-entities"* ]] || [[ "$args" == *"--list-languages"* ]]; then
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

    # Not needed for SLM-only mode
    if [[ "$args" == *"--anonymization-strategy slm"* ]] || [[ "$args" == *"--anonymization-strategy=slm"* ]]; then
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

needs_ollama() {
    local args="$*"

    # Check for SLM-related flags
    if [[ "$args" == *"--slm-"* ]] || [[ "$args" == *"--anonymization-strategy slm"* ]] || [[ "$args" == *"--anonymization-strategy=slm"* ]]; then
        return 0
    fi

    return 1
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
    local model_dir="/app/models/$model"

    log_info "Checking transformer model: $model"

    # Check if model files exist
    if [[ -d "$model_dir" ]] && find "$model_dir" -name "*.safetensors" -o -name "*.bin" 2>/dev/null | grep -q .; then
        log_success "Transformer model '$model' is available"
        return 0
    fi

    log_warn "Transformer model '$model' not found. Downloading..."

    if /app/.venv/bin/python -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='$model', cache_dir='$model_dir', max_workers=4)
print('Download complete')
"; then
        log_success "Transformer model '$model' downloaded successfully"
        return 0
    else
        log_error "Failed to download transformer model '$model'"
        return 1
    fi
}

wait_for_ollama() {
    local url="${OLLAMA_BASE_URL:-http://ollama:11434}"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for Ollama service at $url..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -s "$url/api/tags" > /dev/null 2>&1; then
            log_success "Ollama service is ready"
            return 0
        fi

        log_info "Waiting for Ollama... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    log_error "Ollama service not available after $max_attempts attempts"
    return 1
}

ensure_ollama_model() {
    local model="${OLLAMA_MODEL:-llama3}"
    local url="${OLLAMA_BASE_URL:-http://ollama:11434}"

    log_info "Checking Ollama model: $model"

    # Check if model exists
    local models=$(curl -s "$url/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4)

    if echo "$models" | grep -q "^$model"; then
        log_success "Ollama model '$model' is available"
        return 0
    fi

    log_warn "Ollama model '$model' not found. Pulling..."

    # Pull the model with progress
    curl -s "$url/api/pull" -d "{\"name\": \"$model\"}" | while read -r line; do
        local status=$(echo "$line" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$status" ]]; then
            echo -ne "\r${BLUE}[ollama]${NC} $status                    "
        fi
    done
    echo ""

    log_success "Ollama model '$model' pulled successfully"
    return 0
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
            ollama:*) 
                wait_for_ollama && ensure_ollama_model "${model#ollama:}"
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
    log_info "AnonLFI Container Starting..."

    # Handle preload if specified
    handle_preload

    # Skip lazy loading if disabled
    if [[ "${ANON_LAZY_LOADING:-1}" != "1" ]]; then
        log_info "Lazy loading disabled, running directly"
        exec /app/.venv/bin/python anon.py "$@"
    fi

    # Determine required models based on arguments
    local lang=$(get_language "$@")
    local spacy_model="${lang}_core_news_lg"
    [[ "$lang" == "en" ]] && spacy_model="en_core_web_lg"

    # Provision models as needed
    if needs_spacy_model "$@"; then
        ensure_spacy_model "$spacy_model" || exit 1

        # English is always needed as fallback
        if [[ "$lang" != "en" ]]; then
            ensure_spacy_model "en_core_web_lg" || exit 1
        fi
    fi

    if needs_transformer_model "$@"; then
        ensure_transformer_model "Davlan/xlm-roberta-base-ner-hrl" || exit 1
    fi

    if needs_ollama "$@"; then
        wait_for_ollama || exit 1
        ensure_ollama_model || exit 1
    fi

    # Check if we should run unit tests instead of anon.py
    if [[ "$RUN_UNIT_TESTS" == "1" ]]; then
        log_info "Running unit tests..."
        export PATH="/app/.venv/bin:$PATH"
        export VIRTUAL_ENV="/app/.venv"
        python -m unittest discover -v -s tests/
    else
        log_success "All required models ready. Starting AnonLFI..."
        exec /app/.venv/bin/python anon.py "$@"
    fi
}

# Run main with all arguments
main "$@"
