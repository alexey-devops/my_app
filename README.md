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

## Kubernetes (kind) Quick Start

Для постепенного перехода на K8s добавлен базовый контур в `k8s/`:
- `k8s/base` - namespace, config/secret, postgres, api, worker, frontend, gateway.
- `k8s/overlays/dev` - dev overlay через `kustomize`.

Пошагово:

1. Остановить compose-стек (чтобы не конфликтовать по ресурсам/портам):
```bash
make down
```

2. Поднять локальный кластер и задеплоить базу:
```bash
make k8s-bootstrap
```

3. Проверить состояние:
```bash
make k8s-status
```

4. Открыть приложение:
- `http://localhost:8088`

Полезные команды:
- `make k8s-apply` - повторно применить манифесты
- `make k8s-delete` - удалить манифесты из кластера
- `make k8s-kind-delete` - удалить kind-кластер
- `make k8s-rollout-status K8S_ROLLOUT=deployment/api` - дождаться завершения rollout
- `make k8s-rollout-undo K8S_ROLLOUT=deployment/api` - откатить rollout

### Rolling Update + Rollback demo (2–3 минуты)

Сценарий для собеседования:

1. Вызвать rollout без смены образа (через env timestamp):
```bash
kubectl set env deployment/api -n my-app ROLLOUT_TS=$(date +%s)
```

2. Следить за rollout:
```bash
make k8s-rollout-status K8S_ROLLOUT=deployment/api
```

3. Во время обновления проверить доступность:
```bash
for i in {1..15}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8088/api/health; sleep 1; done
```

4. Откатить деплой:
```bash
make k8s-rollout-undo K8S_ROLLOUT=deployment/api
make k8s-rollout-status K8S_ROLLOUT=deployment/api
```

## Demo Mode (для собеседования)

Чтобы приложение выглядело «живым» без ручных действий:

- в `.env` установи:
  - `WORKER_AUTOPROCESS_ENABLED=0` (worker не перехватывает pending автоматически)
  - `SIMULATOR_ENABLED=1`
  - `SIMULATOR_CREATE_MIN_DELAY_SECONDS=20`
  - `SIMULATOR_CREATE_MAX_DELAY_SECONDS=45`
  - `SIMULATOR_STAGE_MIN_DELAY_SECONDS=15`
  - `SIMULATOR_STAGE_MAX_DELAY_SECONDS=35`
  - `API_LOG_HEALTHCHECKS=0`
- перезапусти сервисы: `make up`

С этого момента `simulator` сам:

1. периодически создаёт задачи,
2. переводит их в `in_progress`,
3. затем в `done` или `failed`,
4. делает это с рандомными «человеческими» паузами.

Дополнительно:

- симулятор удерживает ограниченное количество задач (`SIMULATOR_MAX_TASKS`) и периодически чистит старые записи, чтобы БД не разрасталась бесконечно.

Что показывать в Grafana:

- `Application Lifecycle & Logs`: KPI задач, runtime activity, live API/worker streams.
- `Service Command Center`: внешняя доступность API через Nginx + critical logs.
- `Server Load & Capacity`: нагрузка CPU/RAM/IO во время demo-flow.

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
