.PHONY: build up down test clean db-migrate-head db-revision db-upgrade db-downgrade logs ps compose-validate lint-yaml lint-dockerfiles demo-flow k8s-kind-create k8s-kind-delete k8s-build-images k8s-load-images k8s-apply k8s-delete k8s-status k8s-bootstrap k8s-rollout-status k8s-rollout-undo k8s-monitoring-install k8s-monitoring-uninstall k8s-monitoring-status k8s-main k8s-argocd-install k8s-argocd-status k8s-argocd-ui

# Default to .env if not specified
ENV_FILE ?= .env
DOCKER_COMPOSE ?= docker compose
KIND_CLUSTER_NAME ?= my-app-kind
K8S_NAMESPACE ?= my-app
K8S_OVERLAY ?= k8s/overlays/dev
KIND_TMPDIR ?= $(PWD)/.tmp-kind
K8S_ROLLOUT ?= deployment/api
K8S_ROLLOUT_TIMEOUT ?= 180s
MONITORING_NAMESPACE ?= monitoring
HELM ?= ./scripts/helm.sh
ARGOCD_NAMESPACE ?= argocd

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
	docker build -t my-app/simulator:dev ./simulator

k8s-load-images:
	@echo "Loading images into kind cluster $(KIND_CLUSTER_NAME)..."
	mkdir -p $(KIND_TMPDIR)
	TMPDIR=$(KIND_TMPDIR) kind load docker-image my-app/api:dev --name $(KIND_CLUSTER_NAME)
	TMPDIR=$(KIND_TMPDIR) kind load docker-image my-app/worker:dev --name $(KIND_CLUSTER_NAME)
	TMPDIR=$(KIND_TMPDIR) kind load docker-image my-app/frontend:dev --name $(KIND_CLUSTER_NAME)
	TMPDIR=$(KIND_TMPDIR) kind load docker-image my-app/simulator:dev --name $(KIND_CLUSTER_NAME)

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

k8s-main:
	@echo "Switching to single-source mode: Kubernetes only (compose will be stopped)..."
	$(MAKE) down
	$(MAKE) k8s-build-images
	$(MAKE) k8s-load-images
	$(MAKE) k8s-apply
	$(MAKE) k8s-monitoring-install
	$(MAKE) k8s-status
	@echo "Main app URL: http://localhost:8088"

k8s-monitoring-install:
	@echo "Installing kube-prometheus-stack, Loki and Promtail into namespace $(MONITORING_NAMESPACE)..."
	kubectl create namespace $(MONITORING_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	$(HELM) repo add prometheus-community https://prometheus-community.github.io/helm-charts
	$(HELM) repo add grafana https://grafana.github.io/helm-charts
	$(HELM) repo update
	$(HELM) upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
		-n $(MONITORING_NAMESPACE) \
		-f k8s/monitoring/kube-prometheus-stack-values.yaml
	kubectl wait --for=condition=Established crd/servicemonitors.monitoring.coreos.com --timeout=180s
	kubectl wait --for=condition=Established crd/prometheusrules.monitoring.coreos.com --timeout=180s
	-$(HELM) uninstall loki -n $(MONITORING_NAMESPACE)
	$(HELM) install loki grafana/loki \
		-n $(MONITORING_NAMESPACE) \
		-f k8s/monitoring/loki-values.yaml
	$(HELM) upgrade --install promtail grafana/promtail \
		-n $(MONITORING_NAMESPACE) \
		-f k8s/monitoring/promtail-values.yaml
	kubectl apply -f k8s/monitoring/servicemonitor-api.yaml
	kubectl apply -f k8s/monitoring/servicemonitor-worker.yaml
	kubectl apply -f k8s/monitoring/prometheusrule-app-alerts.yaml
	kubectl apply -f k8s/monitoring/grafana-dashboard-application-lifecycle.yaml
	@echo "Monitoring stack installed."

k8s-monitoring-uninstall:
	@echo "Uninstalling monitoring stack from namespace $(MONITORING_NAMESPACE)..."
	-$(HELM) uninstall promtail -n $(MONITORING_NAMESPACE)
	-$(HELM) uninstall loki -n $(MONITORING_NAMESPACE)
	-$(HELM) uninstall kube-prometheus-stack -n $(MONITORING_NAMESPACE)
	-kubectl delete -f k8s/monitoring/grafana-dashboard-application-lifecycle.yaml --ignore-not-found
	-kubectl delete -f k8s/monitoring/prometheusrule-app-alerts.yaml --ignore-not-found
	-kubectl delete -f k8s/monitoring/servicemonitor-worker.yaml --ignore-not-found
	-kubectl delete -f k8s/monitoring/servicemonitor-api.yaml --ignore-not-found

k8s-monitoring-status:
	@echo "Monitoring namespace resources:"
	kubectl get pods,svc,deploy,sts -n $(MONITORING_NAMESPACE)
	@echo "ServiceMonitors in my-app namespace:"
	kubectl get servicemonitors -n $(K8S_NAMESPACE)
	@echo "PrometheusRules in my-app namespace:"
	kubectl get prometheusrules -n $(K8S_NAMESPACE)

k8s-argocd-install:
	@echo "Installing ArgoCD in namespace $(ARGOCD_NAMESPACE) and applying my-app Application..."
	kubectl create namespace $(ARGOCD_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply --server-side --force-conflicts -n $(ARGOCD_NAMESPACE) -f k8s/argocd/install.yaml
	-kubectl set image deployment/argocd-redis -n $(ARGOCD_NAMESPACE) redis=redis:7-alpine
	kubectl wait --for=condition=Established crd/applications.argoproj.io --timeout=180s
	kubectl rollout status statefulset/argocd-application-controller -n $(ARGOCD_NAMESPACE) --timeout=600s
	kubectl rollout status deployment/argocd-applicationset-controller -n $(ARGOCD_NAMESPACE) --timeout=600s
	kubectl rollout status deployment/argocd-repo-server -n $(ARGOCD_NAMESPACE) --timeout=600s
	kubectl rollout status deployment/argocd-server -n $(ARGOCD_NAMESPACE) --timeout=600s
	-kubectl rollout status deployment/argocd-redis -n $(ARGOCD_NAMESPACE) --timeout=120s
	kubectl apply -f k8s/argocd/application-my-app.yaml
	@echo "ArgoCD installed and Application created."

k8s-argocd-status:
	@echo "ArgoCD resources in namespace $(ARGOCD_NAMESPACE):"
	kubectl get pods,svc,deploy,statefulset -n $(ARGOCD_NAMESPACE)
	@echo "ArgoCD applications:"
	kubectl get applications.argoproj.io -n $(ARGOCD_NAMESPACE)

k8s-argocd-ui:
	@echo "Starting ArgoCD UI port-forward on http://localhost:8080 ..."
	kubectl port-forward -n $(ARGOCD_NAMESPACE) svc/argocd-server 8080:443
