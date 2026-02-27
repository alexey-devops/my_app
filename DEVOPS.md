# DevOps Practices in This Project

Документ фиксирует, какие DevOps-практики реально реализованы в репозитории.

## 1. CI/CD

- Центр CI: Jenkins (`Jenkinsfile` в корне).
- GitHub Actions в репозитории отключены (`.github/workflows-disabled/`).
- Проверки в pipeline:
  - compose config validation;
  - Python autotests (`pytest`);
  - публикация JUnit report;
  - сборка Docker images.

## 2. Контейнеризация

- Все сервисы запускаются через Docker Compose.
- Отдельные Dockerfiles для `api`, `worker`, `frontend`, `jenkins`.
- Runtime в `api` и `worker` выполняется под non-root пользователем.

## 3. Secrets management

- БД и Grafana пароли передаются через Docker secrets:
  - `secrets/postgres_password.txt`
  - `secrets/grafana_admin_password.txt`
- В compose не используется пароль в `DATABASE_URL` для приложений.

## 4. Наблюдаемость

- Метрики: Prometheus.
- Дашборды: Grafana.
- Логи: Loki + Promtail.
- Exporters:
  - `nginx-prometheus-exporter`
  - `redis_exporter`
- Алерты: `compose/monitoring/prometheus/alert_rules.yml`.

## 5. Качество и репозиторий

- Pre-commit hooks (`.pre-commit-config.yaml`):
  - YAML checks
  - detect-private-key
  - merge-conflict check
  - whitespace and EOF hygiene
- Dependabot (`.github/dependabot.yml`) для pip и GitHub Actions зависимостей.

## 6. Operational defaults

- Порты хоста по умолчанию привязаны к `127.0.0.1`.
- `Makefile` использует `docker compose` (не legacy `docker-compose`).
- `make test` гоняет тесты в изолированном Python 3.10 контейнере.

## 7. Ограничения демо-окружения

- Проект ориентирован на локальное/демо окружение.
- Для production отдельно нужны:
  - vault/KMS для секретов;
  - внешние TLS-сертификаты;
  - отдельные role-based права и сегментация сети;
  - hardening host OS и Docker daemon.
