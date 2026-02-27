# Jenkins Setup for This Repository

## 1) Jenkins plugins

Install plugins:
- Pipeline
- Git
- GitHub Integration
- GitHub Branch Source
- JUnit
- Workspace Cleanup
- ANSI Color
- Timestamper

## 2) Jenkins credentials

Create credentials in Jenkins:
- `github-pat` (Kind: Secret text)
  - value: your GitHub PAT with `repo` scope

## 3) Create pipeline job

Recommended: `Pipeline` job with `Pipeline script from SCM`.

SCM settings:
- SCM: `Git`
- Repository URL: `https://github.com/alexey-devops/my_app.git`
- Credentials: `github-pat`
- Branch specifier: `*/feature/*` and `*/main` (or `*/**`)
- Script Path: `Jenkinsfile`

## 4) GitHub webhook

In GitHub repository settings -> Webhooks:
- Payload URL: `http://<jenkins-host>:8080/github-webhook/`
- Content type: `application/json`
- Events: `Just the push event` (and PR if needed)

## 5) Agent requirements

Jenkins agent must have:
- `python3` and `python3-venv`
- `docker` + `docker compose`
- access to Docker daemon (`docker` group)

## 6) What pipeline does

- validates `docker-compose.yml`
- runs `pytest api/tests worker/tests`
- publishes JUnit report
- builds Docker images (`api`, `worker`, `frontend`)

## 7) Interview demo checklist

1. Make code change and push to feature branch.
2. Show Jenkins build auto-start from webhook.
3. Open stages and test report in Jenkins UI.
4. Show successful image build stage.
5. Merge only after green pipeline.
