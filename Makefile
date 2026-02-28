.PHONY: build up down test clean db-migrate-head db-revision db-upgrade db-downgrade logs ps compose-validate lint-yaml lint-dockerfiles

# Default to .env if not specified
ENV_FILE ?= .env
DOCKER_COMPOSE ?= docker compose

all: up

build:
	@echo "Building Docker images..."
	$(DOCKER_COMPOSE) -f docker-compose.yml build
	$(DOCKER_COMPOSE) -f docker-compose.jenkins.yml build

up:
	@echo "Bringing up Docker Compose stack (including Jenkins)..."
	$(DOCKER_COMPOSE) -f docker-compose.yml --env-file $(ENV_FILE) up -d --remove-orphans
	$(DOCKER_COMPOSE) -f docker-compose.jenkins.yml --env-file $(ENV_FILE) up -d --build

down:
	@echo "Bringing down Docker Compose stack (including Jenkins)..."
	$(DOCKER_COMPOSE) -f docker-compose.jenkins.yml --env-file $(ENV_FILE) down -v
	$(DOCKER_COMPOSE) -f docker-compose.yml --env-file $(ENV_FILE) down -v

test:
	@echo "Running Python tests in isolated Python 3.10 container..."
	docker run --rm -v "$(PWD):/work:ro" -w /work python:3.10-slim bash -lc "python -m pip install --upgrade pip >/dev/null && pip install -q -r api/requirements.txt -r worker/requirements.txt pytest && pytest -q -o cache_dir=/tmp/pytest-cache api/tests worker/tests"

clean:
	@echo "Cleaning up Docker resources..."
	$(DOCKER_COMPOSE) -f docker-compose.yml down -v --rmi all
	docker volume prune -f
	docker network prune -f
	@echo "Docker resources cleaned."

# Database migrations with Alembic
DB_MIGRATE_CONTAINER := api

db-migrate-head:
	@echo "Applying all pending Alembic migrations..."
	$(DOCKER_COMPOSE) -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic upgrade head

db-revision: MESSAGE ?= "Empty migration"
db-revision:
	@echo "Creating new Alembic migration: $(MESSAGE)..."
	$(DOCKER_COMPOSE) -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic revision -m "$(MESSAGE)"

db-upgrade: REVISION := head
db-upgrade:
	@echo "Upgrading database to revision $(REVISION)..."
	$(DOCKER_COMPOSE) -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic upgrade $(REVISION)

db-downgrade: REVISION := -1
db-downgrade:
	@echo "Downgrading database to revision $(REVISION)..."
	$(DOCKER_COMPOSE) -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic downgrade $(REVISION)

# Utility targets
logs:
	@echo "Showing Docker Compose logs (including Jenkins)..."
	$(DOCKER_COMPOSE) -f docker-compose.jenkins.yml logs -f
	$(DOCKER_COMPOSE) -f docker-compose.yml logs -f

ps:
	@echo "Listing Docker Compose services (including Jenkins)..."
	$(DOCKER_COMPOSE) -f docker-compose.jenkins.yml ps
	$(DOCKER_COMPOSE) -f docker-compose.yml ps

compose-validate:
	@echo "Validating Docker Compose configuration..."
	docker compose -f docker-compose.yml --env-file $(ENV_FILE) config >/tmp/compose.validated.yml
	docker compose -f docker-compose.jenkins.yml --env-file $(ENV_FILE) config >/tmp/compose.jenkins.validated.yml
	@echo "Compose config is valid."

lint-yaml:
	@echo "Linting YAML files with yamllint container..."
	docker run --rm -v "$(PWD):/data" cytopia/yamllint -c /data/.yamllint.yml /data

lint-dockerfiles:
	@echo "Linting Dockerfiles with hadolint container..."
	docker run --rm -i --entrypoint hadolint -v "$(PWD):/work" hadolint/hadolint --config /work/.hadolint.yaml /work/api/Dockerfile
	docker run --rm -i --entrypoint hadolint -v "$(PWD):/work" hadolint/hadolint --config /work/.hadolint.yaml /work/worker/Dockerfile
	docker run --rm -i --entrypoint hadolint -v "$(PWD):/work" hadolint/hadolint --config /work/.hadolint.yaml /work/frontend/Dockerfile
