# My App: Task Lifecycle Platform

Демонстрационный DevOps-oriented проект: API + worker + UI + мониторинг + Jenkins CI.

## Что внутри

- `api/` - FastAPI сервис для задач.
- `worker/` - фоновый обработчик жизненного цикла задач.
- `frontend/` - веб-интерфейс для управления задачами.
- `nginx/` - единая точка входа с HTTPS.
- `compose/monitoring/` - Prometheus, Grafana, Loki, exporters.
- `Jenkinsfile` - основной CI pipeline.

## Жизненный цикл задач

- `pending` -> `in_progress` -> `done`
- В `failed` задача попадает, если:
  - в title есть маркер `[FAIL]`, или
  - срабатывает вероятностная ошибка `WORKER_FAILURE_RATE`.
- Для `failed` в UI доступен `Retry` (перевод обратно в `pending`).

## Быстрый старт

1. Создать `.env`:

```bash
cp .env.example .env
```

2. Подготовить секреты:

```bash
mkdir -p secrets certs
echo "<postgres-password>" > secrets/postgres_password.txt
echo "<grafana-password>" > secrets/grafana_admin_password.txt
```

3. Поднять сервисы:

```bash
make up
```

4. Проверить:

- UI: `https://localhost:8443/`
- API: `https://localhost:8443/api/health`
- Grafana: `https://localhost:8443/grafana/`
- Prometheus: `https://localhost:8443/prometheus/`

## Безопасные дефолты

- Пароли не передаются через `DATABASE_URL` в compose.
- Пароли читаются из Docker secrets (`/run/secrets/...`).
- Внешние порты по умолчанию привязаны к `127.0.0.1`.
- `GET /` в API не раскрывает информацию о строке подключения к БД.

## Тесты

Запуск в изолированном контейнере Python 3.10 (как в Jenkins):

```bash
make test
```

## CI (Jenkins)

Pipeline стадии:

1. `Checkout`
2. `Prepare CI Environment`
3. `Validate Compose`
4. `Autotests`
5. `Build Docker Images`

Техническая пометка: не-функциональное тестовое изменение в ветке `test`.

Подробная настройка:

- [JENKINS.md](JENKINS.md)
- [JENKINS_LOCAL.md](JENKINS_LOCAL.md)
- [DEVOPS.md](DEVOPS.md)

Для "только после CI в main": включи branch protection на `main` и обязательный status check `ci/jenkins` (см. `JENKINS.md`).

## Структура статусов API

- `POST /tasks`
- `GET /tasks?status=<status>&limit=<n>&offset=<n>`
- `GET /tasks/{id}`
- `PATCH /tasks/{id}/status`
