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

Дополнительно в `Jenkinsfile` включён `pollSCM('H/2 * * * *')` как fallback.
Это страхует CI, если webhook временно недоступен (статусы для PR не зависают в `pending`).

## 7) Обязательный gate перед попаданием в `main`

Важно: модель "сначала Jenkins, потом push в GitHub" для GitHub технически невозможна, потому что Jenkins запускается после события в GitHub. Корректный и безопасный вариант: запретить прямые push в `main` и разрешать только merge PR после успешного Jenkins check.

Сделай так в GitHub -> `Settings` -> `Branches` -> `Add branch protection rule` для `main`:

- Включи `Require a pull request before merging`.
- Включи `Require status checks to pass before merging`.
- Добавь обязательный check: `ci/jenkins`.
- Включи `Require branches to be up to date before merging`.
- Включи `Restrict who can push to matching branches` (или полностью запрети push в `main` для обычных участников).

После этого поток будет таким:

1. Разработчик пушит в feature-ветку.
2. Jenkins запускается и ставит статус `ci/jenkins`.
3. Пока статус не зелёный, GitHub не даст смержить PR в `main`.
4. В `main` попадают только изменения, прошедшие Jenkins.
