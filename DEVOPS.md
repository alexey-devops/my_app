# DevOps Toolkit in This Project

Этот документ описывает DevOps-практики и инструменты, которые реализованы в проекте для демонстрации инженерной зрелости.

## CI/CD

### Jenkins Pipeline

- `Jenkinsfile` (корень репозитория)
  - `Checkout`
  - `Prepare CI Environment` (venv + deps + test fixtures)
  - `Validate Compose`
  - `Unit Tests` (`pytest` + JUnit report)
  - `Build Docker Images` (api/worker/frontend)

### GitHub role

- GitHub используется как source-of-truth для репозитория.
- Автозапуск CI через GitHub Actions отключён:
  - workflow-файлы перенесены в `.github/workflows-disabled/`

## Dependency Management

- Зависимости ревьюятся и обновляются через обычный git-flow с прогоном Jenkins pipeline.

## Quality Gates

- `.yamllint.yml` — правила линтинга YAML
- `.hadolint.yaml` — правила линтинга Dockerfile
- `.pre-commit-config.yaml` — pre-commit hooks:
  - check-yaml
  - trailing-whitespace
  - end-of-file-fixer
  - detect-private-key
  - check-added-large-files

## Monitoring

- Prometheus + Grafana + Loki в `docker-compose.yml`
- Exporters:
  - `nginx-prometheus-exporter`
  - `redis_exporter`
- Prometheus rules:
  - `compose/monitoring/prometheus/alert_rules.yml` (`TargetDown`)

## Local Ops Commands

Через `Makefile`:

- `make compose-validate` — проверка compose-конфига
- `make lint-yaml` — линт YAML
- `make lint-dockerfiles` — линт Dockerfile
- `make test` — Python-тесты
- `make up / make down` — запуск/остановка стека

## Release Flow (recommended)

1. Push в feature-ветку.
2. Jenkins запускает pipeline по webhook.
3. После зелёного pipeline — merge в `main`.
4. Jenkins release job (отдельная) собирает и публикует образы в registry.
