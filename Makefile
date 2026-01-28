# =============================================================================
# AnonLFI - Makefile
# =============================================================================
# Convenient commands for building and running AnonLFI containers
#
# Usage:
#   make build          - Build CPU image
#   make build-gpu      - Build GPU image
#   make run FILE=input.txt  - Run anonymization on a file
#   make slm-up         - Start Ollama service
#   make shell          - Open interactive shell in container
# =============================================================================

.PHONY: help build build-gpu run run-gpu slm-up slm-down shell clean logs test

# Default target
help:
	@echo "AnonLFI Docker Commands"
	@echo "======================="
	@echo ""
	@echo "Build:"
	@echo "  make build          Build CPU image"
	@echo "  make build-gpu      Build GPU-accelerated image"
	@echo "  make build-all      Build both images"
	@echo ""
	@echo "Run:"
	@echo "  make run FILE=<path>           Anonymize a file (CPU)"
	@echo "  make run-gpu FILE=<path>       Anonymize a file (GPU)"
	@echo "  make run-slm FILE=<path>       Anonymize with SLM features"
	@echo "  make shell                     Interactive shell in container"
	@echo ""
	@echo "Services:"
	@echo "  make slm-up         Start Ollama service"
	@echo "  make slm-down       Stop Ollama service"
	@echo "  make pull-model MODEL=llama3   Pull an Ollama model"
	@echo ""
	@echo "Maintenance:"
	@echo "  make logs           Show container logs"
	@echo "  make clean          Remove containers and images"
	@echo "  make clean-volumes  Remove all data volumes (DESTRUCTIVE)"
	@echo ""
	@echo "Examples:"
	@echo "  make run FILE=./data/input.json"
	@echo "  make run-slm FILE=./data/input.json ARGS='--slm-map-entities'"
	@echo "  make pull-model MODEL=llama3"

# =============================================================================
# Build Targets
# =============================================================================

build:
	@echo "Building AnonLFI CPU image..."
	docker-compose build anon

build-gpu:
	@echo "Building AnonLFI GPU image..."
	docker-compose --profile gpu build anon-gpu

build-all: build build-gpu
	@echo "All images built successfully"

# =============================================================================
# Run Targets
# =============================================================================

# Run anonymization on a file (CPU version)
run:
ifndef FILE
	$(error FILE is required. Usage: make run FILE=./data/input.txt)
endif
	@echo "Running AnonLFI on $(FILE)..."
	docker-compose run --rm anon $(FILE) $(ARGS)

# Run anonymization on a file (GPU version)
run-gpu:
ifndef FILE
	$(error FILE is required. Usage: make run-gpu FILE=./data/input.txt)
endif
	@echo "Running AnonLFI (GPU) on $(FILE)..."
	docker-compose --profile gpu run --rm anon-gpu $(FILE) $(ARGS)

# Run with SLM features enabled
run-slm:
ifndef FILE
	$(error FILE is required. Usage: make run-slm FILE=./data/input.txt)
endif
	@echo "Starting Ollama if not running..."
	@docker-compose --profile slm up -d ollama
	@echo "Waiting for Ollama to be ready..."
	@sleep 5
	@echo "Running AnonLFI with SLM on $(FILE)..."
	docker-compose --profile slm run --rm anon $(FILE) $(ARGS)

# Interactive shell
shell:
	docker-compose run --rm --entrypoint /bin/bash anon

# Show help
anon-help:
	docker-compose run --rm anon --help

# =============================================================================
# Service Management
# =============================================================================

# Start Ollama service
slm-up:
	@echo "Starting Ollama service..."
	docker-compose --profile slm up -d ollama
	@echo "Waiting for Ollama to be ready..."
	@sleep 5
	@docker-compose --profile slm exec ollama curl -s http://localhost:11434/api/tags | head -1
	@echo "Ollama is ready!"

# Stop Ollama service
slm-down:
	@echo "Stopping Ollama service..."
	docker-compose --profile slm down

# Start Ollama with GPU
slm-up-gpu:
	@echo "Starting Ollama with GPU..."
	docker-compose --profile gpu up -d ollama-gpu

# Pull an Ollama model
pull-model:
ifndef MODEL
	$(error MODEL is required. Usage: make pull-model MODEL=llama3)
endif
	@echo "Pulling model $(MODEL)..."
	docker-compose --profile slm exec ollama ollama pull $(MODEL)

# List available Ollama models
list-models:
	@docker-compose --profile slm exec ollama ollama list 2>/dev/null || echo "Ollama not running. Start with: make slm-up"

# =============================================================================
# Logs and Debugging
# =============================================================================

logs:
	docker-compose logs -f

logs-ollama:
	docker-compose --profile slm logs -f ollama

# =============================================================================
# Cleanup
# =============================================================================

# Stop all containers
down:
	docker-compose --profile slm --profile gpu down

# Remove containers and images
clean: down
	@echo "Removing AnonLFI images..."
	-docker rmi anon:latest anon:gpu 2>/dev/null || true
	@echo "Cleanup complete"

# Remove all volumes (DESTRUCTIVE - removes downloaded models!)
clean-volumes:
	@echo "WARNING: This will delete all downloaded models and data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker-compose --profile slm --profile gpu down -v
	-docker volume rm anon-models anon-output anon-db ollama-models 2>/dev/null || true
	@echo "All volumes removed"

# Full cleanup
clean-all: clean clean-volumes
	@echo "Full cleanup complete"

# =============================================================================
# Development
# =============================================================================

# Run tests inside container
test:
	docker-compose run --rm --entrypoint "" anon uv run pytest tests/

# Lint code
lint:
	docker-compose run --rm --entrypoint "" anon uv run ruff check .

# =============================================================================
# Quick Start
# =============================================================================

# First-time setup
setup:
	@echo "Setting up AnonLFI..."
	@cp -n .env.example .env 2>/dev/null || true
	@mkdir -p data
	@echo "Building images..."
	@$(MAKE) build
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "  1. Edit .env with your ANON_SECRET_KEY"
	@echo "  2. Place input files in ./data/"
	@echo "  3. Run: make run FILE=/data/yourfile.txt"
	@echo ""
	@echo "For SLM features:"
	@echo "  1. Run: make slm-up"
	@echo "  2. Run: make pull-model MODEL=llama3"
	@echo "  3. Run: make run-slm FILE=/data/yourfile.txt ARGS='--slm-map-entities'"
