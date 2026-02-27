# Local Jenkins (docker-compose.jenkins.yml)

## Запуск

```bash
docker compose -f docker-compose.jenkins.yml up -d --build
```

Jenkins UI:

- `http://localhost:8081`

Порты в compose привязаны к `127.0.0.1`.

## Локальный админ-пользователь

`jenkins/init.groovy.d/01-security.groovy` на старте создаёт локального admin user.

Переменные:

- `JENKINS_ADMIN_USER` (default: `admin`)
- `JENKINS_ADMIN_PASSWORD`

Если `JENKINS_ADMIN_PASSWORD` пустой, генерируется одноразовый пароль и выводится в логи контейнера:

```bash
docker logs jenkins | tail -n 50
```

## Остановка

```bash
docker compose -f docker-compose.jenkins.yml down
```

## Рекомендуемая настройка job

1. `New Item` -> `Pipeline`
2. `Pipeline script from SCM`
3. Repository: `https://github.com/alexey-devops/my_app.git`
4. Branch: `*/main`
5. Script path: `Jenkinsfile`

## Что делает pipeline

- проверяет `docker-compose.yml`
- запускает автотесты `pytest` в Python 3.10 контейнере
- публикует JUnit (`reports/pytest.xml`)
- публикует coverage (`reports/coverage.xml`)
- собирает Docker images (`api`, `worker`, `frontend`)
