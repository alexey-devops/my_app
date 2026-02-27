# Local Jenkins in this repository

## Start

```bash
docker compose -f docker-compose.jenkins.yml up -d --build
```

## Open UI

- URL: `http://localhost:8081`
- Login: `admin`
- Password: `admin123`

## Stop

```bash
docker compose -f docker-compose.jenkins.yml down
```

## Pipeline setup in UI

1. `New Item` -> `Pipeline` -> name: `my_app_pipeline`
2. `Pipeline` -> `Pipeline script from SCM`
3. SCM: `Git`
4. Repository URL: `https://github.com/alexey-devops/my_app.git`
5. Branch: `*/feature/tasks-api-mvp` (or `*/main`)
6. Script Path: `Jenkinsfile`
7. Save -> `Build Now`

## Webhook

In GitHub repository settings add webhook:
- `http://<your-host>:8081/github-webhook/`
- event: `push`
