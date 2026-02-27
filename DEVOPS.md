# DevOps Toolkit in This Project

Этот документ описывает DevOps-практики и инструменты, которые реализованы в проекте для демонстрации инженерной зрелости.

## CI/CD

### Workflows

- `.github/workflows/ci-cd.yml`
  - Python тесты (`pytest`)
  - Сборка Docker-образов API/Worker/Frontend

- `.github/workflows/devops-quality.yml`
  - Валидация `docker-compose.yml`
  - `yamllint` для YAML
  - `hadolint` для Dockerfile
  - `Trivy` FS scan с загрузкой SARIF в Security tab GitHub

- `.github/workflows/release-images.yml`
  - Release-пайплайн по тегам `v*.*.*`
  - Публикация образов в GHCR:
    - `ghcr.io/<owner>/my-app-api`
    - `ghcr.io/<owner>/my-app-worker`
    - `ghcr.io/<owner>/my-app-frontend`

## Dependency Management

- `.github/dependabot.yml`
  - автоматические weekly-обновления:
    - GitHub Actions
    - Python dependencies (`api`, `worker`)

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

1. Merge в `main`
2. Создать тег версии:
   - `git tag v1.0.0`
   - `git push origin v1.0.0`
3. GitHub Actions автоматически соберёт и опубликует образы в GHCR
