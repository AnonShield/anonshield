# AnonShield ops. Run from the web/ directory on the host.
# Every target is one obvious command. Type `make` (or `make help`) to list them.
#
#   make deploy     build, start, warm the cache, show status (the usual command)
#   make status     what is running and is it healthy
#   make logs       follow logs (make logs SVC=backend to filter)
#   make restart    restart the stack
#   make warm       preload the NER model so the first request is fast
#   make down       stop everything
#
# This wraps docker compose with the production file plus the host override
# (docker-compose.host.yml: localhost ports for the host Caddy, reduced memory).

COMPOSE  := docker compose -f docker-compose.prod.yml -f docker-compose.host.yml
SERVICES := backend frontend worker-fast redis
BACKEND  := http://127.0.0.1:18000
SVC      ?=

.DEFAULT_GOAL := help

.PHONY: help deploy build up down restart status ps health logs stats warm shell clean

help:  ## List the available commands
	@echo "AnonShield ops. Usage: make <target>"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

deploy: build up warm status  ## Build, start, warm the cache, and show status (full deploy)
	@echo "Deployed. Public URL: https://anonshield.org"

build:  ## Build the container images
	$(COMPOSE) build $(SERVICES)

up:  ## Start the stack (no rebuild)
	$(COMPOSE) up -d $(SERVICES)

down:  ## Stop and remove the containers
	$(COMPOSE) down

restart:  ## Restart the stack
	$(COMPOSE) restart $(SERVICES)

status ps:  ## Show container status and health
	@$(COMPOSE) ps

health:  ## Check the backend health endpoint
	@curl -fsS $(BACKEND)/api/health && echo "  (ok)" || echo "backend not healthy"

logs:  ## Follow logs. Filter with: make logs SVC=backend
	$(COMPOSE) logs -f --tail=120 $(SVC)

stats:  ## Live CPU and memory usage of the containers
	docker stats $$($(COMPOSE) ps -q)

warm:  ## Preload the NER model cache (first request is slow otherwise)
	@bash warm_cache.sh $(BACKEND)

shell:  ## Open a shell inside the backend container
	$(COMPOSE) exec backend sh

clean:  ## Reclaim disk: prune build cache and dangling images (safe)
	docker builder prune -af && docker image prune -f
