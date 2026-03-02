.PHONY: build up down test clean db-migrate-head db-revision db-upgrade db-downgrade logs ps compose-validate lint-yaml lint-dockerfiles demo-flow k8s-kind-create k8s-kind-delete k8s-build-images k8s-load-images k8s-apply k8s-delete k8s-status k8s-bootstrap k8s-rollout-status k8s-rollout-undo

# Default to .env if not specified
ENV_FILE ?= .env
DOCKER_COMPOSE ?= docker compose
KIND_CLUSTER_NAME ?= my-app-kind
K8S_NAMESPACE ?= my-app
K8S_OVERLAY ?= k8s/overlays/dev
KIND_TMPDIR ?= $(PWD)/.tmp-kind
K8S_ROLLOUT ?= deployment/api
K8S_ROLLOUT_TIMEOUT ?= 180s

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

demo-flow:
	@echo "Generating live demo events in API/worker..."
	./scripts/demo_flow.sh "$(DEMO_BASE_URL)"

k8s-kind-create:
	@echo "Creating kind cluster $(KIND_CLUSTER_NAME)..."
	kind create cluster --name $(KIND_CLUSTER_NAME) --config k8s/kind-config.yaml

k8s-kind-delete:
	@echo "Deleting kind cluster $(KIND_CLUSTER_NAME)..."
	kind delete cluster --name $(KIND_CLUSTER_NAME)

k8s-build-images:
	@echo "Building local images for kind..."
	docker build -t my-app/api:dev ./api
	docker build -t my-app/worker:dev ./worker
	docker build -t my-app/frontend:dev ./frontend

k8s-load-images:
	@echo "Loading images into kind cluster $(KIND_CLUSTER_NAME)..."
	mkdir -p $(KIND_TMPDIR)
	TMPDIR=$(KIND_TMPDIR) kind load docker-image my-app/api:dev --name $(KIND_CLUSTER_NAME)
	TMPDIR=$(KIND_TMPDIR) kind load docker-image my-app/worker:dev --name $(KIND_CLUSTER_NAME)
	TMPDIR=$(KIND_TMPDIR) kind load docker-image my-app/frontend:dev --name $(KIND_CLUSTER_NAME)

k8s-apply:
	@echo "Applying Kubernetes manifests from $(K8S_OVERLAY)..."
	kubectl apply -k $(K8S_OVERLAY)

k8s-delete:
	@echo "Deleting Kubernetes manifests from $(K8S_OVERLAY)..."
	kubectl delete -k $(K8S_OVERLAY) --ignore-not-found

k8s-status:
	@echo "Kubernetes resources in namespace $(K8S_NAMESPACE):"
	kubectl get pods,svc,deploy -n $(K8S_NAMESPACE)

k8s-bootstrap: k8s-kind-create k8s-build-images k8s-load-images k8s-apply k8s-status
	@echo "kind bootstrap completed. App gateway is exposed on http://localhost:8088"

k8s-rollout-status:
	@echo "Waiting rollout status for $(K8S_ROLLOUT) in namespace $(K8S_NAMESPACE)..."
	kubectl rollout status $(K8S_ROLLOUT) -n $(K8S_NAMESPACE) --timeout=$(K8S_ROLLOUT_TIMEOUT)

k8s-rollout-undo:
	@echo "Rolling back $(K8S_ROLLOUT) in namespace $(K8S_NAMESPACE)..."
	kubectl rollout undo $(K8S_ROLLOUT) -n $(K8S_NAMESPACE)
