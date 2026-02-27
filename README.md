# My App: Tasks Platform Demo

Демонстрационный full-stack проект на Docker Compose: API, worker, PostgreSQL, Redis, Nginx и стек наблюдаемости.

## Что реализовано

- `API (FastAPI)`:
  - `GET /health`
  - `POST /tasks` — создать задачу
  - `GET /tasks` — список задач с фильтрацией по статусу и пагинацией
  - `GET /tasks/{id}` — получить задачу
  - `PATCH /tasks/{id}/status` — изменить статус
- `Worker`:
  - выбирает задачи `pending`
  - резервирует в `in_progress`
  - переводит в `done` (или `failed` при ошибке)
- `Frontend`:
  - живой dashboard задач
  - создание задач, фильтр и смена статуса
- `DB schema`:
  - Alembic ревизия `20260227_01` для таблицы `tasks`
- `CI`:
  - запуск unit/integration-тестов
  - сборка Docker-образов

## Технологии

- Python 3.10
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL, Redis
- Nginx
- Docker / Docker Compose
- GitHub Actions

## Запуск локально

1. Создать `.env` из шаблона:

```bash
cp .env.example .env
```

2. Заполнить секреты:

```bash
echo "<postgres-password>" > secrets/postgres_password.txt
echo "<grafana-password>" > secrets/grafana_admin_password.txt
```

3. Поднять стек:

```bash
make up
```

4. Открыть сервисы:

- Frontend: `https://localhost:8443/`
- API через Nginx: `https://localhost:8443/api/health`
- Grafana: `https://localhost:8443/grafana/`
- Prometheus: `https://localhost:8443/prometheus/`

## Миграции

Применить все миграции:

```bash
make db-migrate-head
```

Создать новую ревизию:

```bash
make db-revision MESSAGE="описание"
```

## Тесты

```bash
make test
```

## Структура

- `api/` — REST API + Alembic + тесты
- `worker/` — обработчик фоновых задач + тесты
- `frontend/` — статический UI (Nginx)
- `compose/monitoring/` — Prometheus/Grafana/Loki
- `nginx/` — reverse proxy конфигурация

## Статусы задач

- `pending`
- `in_progress`
- `done`
- `failed`
