.PHONY: build up down test clean db-migrate-head db-revision db-upgrade db-downgrade

# Default to .env if not specified
ENV_FILE ?= .env

all: up

build:
	@echo "Building Docker images..."
	docker-compose -f docker-compose.yml build

up:
	@echo "Bringing up Docker Compose stack..."
	docker-compose -f docker-compose.yml --env-file $(ENV_FILE) up -d --remove-orphans

down:
	@echo "Bringing down Docker Compose stack..."
	docker-compose -f docker-compose.yml --env-file $(ENV_FILE) down -v

test:
	@echo "Running tests (placeholder)..."
	# Add your test commands here

clean:
	@echo "Cleaning up Docker resources..."
	docker-compose -f docker-compose.yml down -v --rmi all
	docker volume prune -f
	docker network prune -f
	@echo "Docker resources cleaned."

# Database migrations with Alembic
DB_MIGRATE_CONTAINER := api

db-migrate-head:
	@echo "Applying all pending Alembic migrations..."
	docker-compose -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic upgrade head

db-revision: MESSAGE ?= "Empty migration"
db-revision:
	@echo "Creating new Alembic migration: $(MESSAGE)..."
	docker-compose -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic revision -m "$(MESSAGE)"

db-upgrade: REVISION := head
db-upgrade:
	@echo "Upgrading database to revision $(REVISION)..."
	docker-compose -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic upgrade $(REVISION)

db-downgrade: REVISION := -1
db-downgrade:
	@echo "Downgrading database to revision $(REVISION)..."
	docker-compose -f docker-compose.yml --env-file $(ENV_FILE) exec $(DB_MIGRATE_CONTAINER) alembic downgrade $(REVISION)

# Utility targets
logs:
	@echo "Showing Docker Compose logs..."
	docker-compose -f docker-compose.yml logs -f

ps:
	@echo "Listing Docker Compose services..."
	docker-compose -f docker-compose.yml ps
