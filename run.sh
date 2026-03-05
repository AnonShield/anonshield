#!/bin/bash
# =============================================================================
# AnonLFI - Docker Compose Wrapper with Auto-Provisioning
# =============================================================================
#
# Automatically selects the Docker Compose profile based on CLI arguments
# and provisions required services (Ollama, GPU) on demand.
#
# Usage:
#   ./run.sh input.txt                          # CPU, no SLM
#   ./run.sh input.txt --slm-detector           # CPU + Ollama
#   ./run.sh --gpu input.txt                    # GPU, no SLM
#   ./run.sh --gpu input.txt --slm-detector     # GPU + Ollama (GPU)
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker/docker-compose.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[run.sh]${NC} $1"; }
log_success() { echo -e "${GREEN}[run.sh]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[run.sh]${NC} $1"; }
log_error()   { echo -e "${RED}[run.sh]${NC} $1"; }

# =============================================================================
# Detect required features from CLI arguments
# =============================================================================

detect_profile() {
    local use_gpu=0
    local use_slm=0

    for arg in "$@"; do
        case "$arg" in
            --gpu)
                use_gpu=1
                ;;
            --slm-*|--anonymization-strategy=slm)
                use_slm=1
                ;;
        esac
    done

    # Also check two-word form: --anonymization-strategy slm
    local args="$*"
    if [[ "$args" == *"--anonymization-strategy slm"* ]]; then
        use_slm=1
    fi

    if [[ $use_gpu -eq 1 && $use_slm -eq 1 ]]; then
        echo "gpu-slm"
    elif [[ $use_gpu -eq 1 ]]; then
        echo "gpu"
    elif [[ $use_slm -eq 1 ]]; then
        echo "slm"
    else
        echo "cpu"
    fi
}

# =============================================================================
# Validation
# =============================================================================

validate() {
    if ! docker info &>/dev/null; then
        log_error "Docker is not running."
        exit 1
    fi

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose.yml not found at $COMPOSE_FILE"
        log_error "Run this script from the project root."
        exit 1
    fi

    # Warn if no secret key (unless help/list commands)
    local args="$*"
    if [[ "$args" != *"--help"* ]] && \
       [[ "$args" != *"--list-"* ]] && \
       [[ -z "${ANON_SECRET_KEY:-}" ]]; then
        log_warn "ANON_SECRET_KEY is not set. Set it with: export ANON_SECRET_KEY='your-key'"
    fi
}

check_gpu() {
    # Try standard --gpus all first
    if docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
        echo "standard"
        return 0
    fi
    
    # Fallback to explicit --runtime=nvidia for problematic systems
    if docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
        echo "runtime"
        return 0
    fi
    
    log_error "GPU requested but NVIDIA Docker runtime is not available."
    log_error "Install NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    log_warn "Falling back to CPU."
    return 1
}

# =============================================================================
# Service management
# =============================================================================

start_ollama() {
    local profile="$1"
    local service=""

    case "$profile" in
        slm)     service="ollama" ;;
        gpu-slm) service="ollama-gpu" ;;
        *)       return 0 ;;
    esac

    log_info "Starting $service service..."
    docker compose -f "$COMPOSE_FILE" --profile "$profile" up -d "$service"

    # Wait for healthcheck
    local attempts=0
    local max=30
    while [[ $attempts -lt $max ]]; do
        if docker compose -f "$COMPOSE_FILE" --profile "$profile" ps "$service" 2>/dev/null | grep -q "healthy"; then
            log_success "$service is ready."
            return 0
        fi
        # Also accept "running" for services that respond but healthcheck hasn't fired yet
        local url="http://localhost:11434/api/tags"
        if curl -sf "$url" &>/dev/null; then
            log_success "$service is ready."
            return 0
        fi
        sleep 2
        ((attempts++))
    done

    log_warn "$service health check not confirmed after ${max} attempts, proceeding anyway."
}

# =============================================================================
# Main
# =============================================================================

main() {
    validate "$@"

    local profile
    profile=$(detect_profile "$@")

    # GPU validation with fallback
    local gpu_mode=""
    if [[ "$profile" == gpu* ]]; then
        gpu_mode=$(check_gpu) || {
            # Fallback: strip gpu, keep slm if present
            if [[ "$profile" == "gpu-slm" ]]; then
                profile="slm"
            else
                profile="cpu"
            fi
            gpu_mode=""
        }
    fi

    log_info "Profile: $profile"

    # Start background services (Ollama) if needed
    start_ollama "$profile"

    # Build args for anon.py (strip --gpu which is run.sh-only)
    local anon_args=()
    for arg in "$@"; do
        [[ "$arg" != "--gpu" ]] && anon_args+=("$arg")
    done

    # Select container service
    local service="anon"
    [[ "$profile" == gpu* ]] && service="anon-gpu"

    log_info "Running AnonLFI ($service)..."
    
    # For GPU profiles, use appropriate Docker GPU configuration
    if [[ "$profile" == gpu* ]]; then
        local docker_args=(
            "--rm"
            "--gpus" "all"
            "-e" "ANON_SECRET_KEY=${ANON_SECRET_KEY:-change-me-in-production}"
            "-e" "ANON_LAZY_LOADING=1"
            "-e" "NVIDIA_VISIBLE_DEVICES=all"
            "-e" "NVIDIA_DRIVER_CAPABILITIES=compute,utility"
            "-v" "anon-models:/app/models"
            "-v" "anon-output:/app/output"
            "-v" "anon-db:/app/db"
            "-v" "${DATA_DIR:-$(pwd)/../data}:/data:ro"
        )
        
        # Add --runtime=nvidia for problematic systems
        if [[ "$gpu_mode" == "runtime" ]]; then
            log_info "Using explicit NVIDIA runtime for GPU acceleration..."
            docker_args=("--runtime=nvidia" "${docker_args[@]}")
        fi
        
        local image="anonshield/anon:gpu"
        docker run "${docker_args[@]}" "$image" "${anon_args[@]}"
    else
        docker compose -f "$COMPOSE_FILE" --profile "$profile" run --rm "$service" "${anon_args[@]}"
    fi
}

main "$@"
