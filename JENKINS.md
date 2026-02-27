# Jenkins Setup (Repository Pipeline)

## 1) Plugins

Минимально необходимые:

- Pipeline
- Git
- GitHub / GitHub Integration
- JUnit
- Timestamper

Опционально:

- Blue Ocean

Примечание: `ansiColor` и `ws-cleanup` pipeline не требует.

## 2) Credentials

Создай credential для доступа к репозиторию:

- ID: `github-pat`
- Type: `Secret text`
- Value: GitHub PAT со scope `repo`

## 3) Pipeline job

Тип: `Pipeline` -> `Pipeline script from SCM`

- SCM: `Git`
- Repository URL: `https://github.com/alexey-devops/my_app.git`
- Credentials: `github-pat`
- Branch: `*/main`
- Script Path: `Jenkinsfile`

## 4) Agent requirements

Текущий `Jenkinsfile` запускает автотесты внутри `python:3.10-slim` контейнера, поэтому от Jenkins/агента требуется:

- Docker CLI + доступ к Docker daemon
- Docker Compose v2 (`docker compose`)
- доступ в интернет для установки pip dependencies внутри test container

## 5) Stage breakdown

1. `Checkout`
2. `Prepare CI Environment`
3. `Validate Compose`
4. `Autotests`
5. `Build Docker Images`

## 6) Автозапуск по push (webhook)

1. В Jenkins job включи trigger:
   `GitHub hook trigger for GITScm polling`.
2. В GitHub Repo -> Settings -> Webhooks:
   - Payload URL: `http://<jenkins-host>:8080/github-webhook/`
   - Content type: `application/json`
   - Event: `Just the push event`
3. Проверь `Recent Deliveries` в GitHub (ожидается HTTP 200).
