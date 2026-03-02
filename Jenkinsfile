def setGithubStatus(String state, String description) {
  def statusCredentialId = env.GITHUB_STATUS_CREDENTIALS_ID ?: 'my-app'
  def remoteUrl = (env.GIT_URL ?: '').trim()
  def sha = (env.GIT_COMMIT ?: '').trim()

  if (!remoteUrl) {
    remoteUrl = sh(script: "git config --get remote.origin.url 2>/dev/null || true", returnStdout: true).trim()
  }
  if (!sha) {
    sha = sh(script: "git rev-parse HEAD 2>/dev/null || true", returnStdout: true).trim()
  }

  def repoSlug = ''
  if (remoteUrl.startsWith('git@github.com:')) {
    repoSlug = remoteUrl.replace('git@github.com:', '').replaceAll(/\.git$/, '')
  } else if (remoteUrl.startsWith('https://github.com/')) {
    repoSlug = remoteUrl.replace('https://github.com/', '').replaceAll(/\.git$/, '')
  }

  if (!repoSlug || !sha) {
    echo "Skipping GitHub status update: could not resolve repo/sha (remote='${remoteUrl}', sha='${sha}')"
    return
  }

  def targetUrl = resolveBuildUrl()

  def publishWithTokenHeader = {
    sh """
      set -euo pipefail
      cat > /tmp/github-status.json <<JSON
{"state":"${state}","context":"ci/jenkins","description":"${description}","target_url":"${targetUrl}"}
JSON
      curl -fsS -X POST \\
        -H "Authorization: token \$GITHUB_TOKEN" \\
        -H "Accept: application/vnd.github+json" \\
        "https://api.github.com/repos/${repoSlug}/statuses/${sha}" \\
        -d @/tmp/github-status.json >/dev/null
    """
  }

  def publishWithBasicAuth = {
    sh """
      set -euo pipefail
      cat > /tmp/github-status.json <<JSON
{"state":"${state}","context":"ci/jenkins","description":"${description}","target_url":"${targetUrl}"}
JSON
      curl -fsS -X POST \\
        -u "\$GITHUB_USER:\$GITHUB_TOKEN" \\
        -H "Accept: application/vnd.github+json" \\
        "https://api.github.com/repos/${repoSlug}/statuses/${sha}" \\
        -d @/tmp/github-status.json >/dev/null
    """
  }

  try {
    withCredentials([string(credentialsId: statusCredentialId, variable: 'GITHUB_TOKEN')]) {
      publishWithTokenHeader()
    }
    return
  } catch (Exception ignored) {
    // Fallback to username/password credentials type.
  }

  try {
    withCredentials([usernamePassword(credentialsId: statusCredentialId, usernameVariable: 'GITHUB_USER', passwordVariable: 'GITHUB_TOKEN')]) {
      publishWithBasicAuth()
    }
  } catch (Exception e) {
    echo "Skipping GitHub status update: ${e.getMessage()}"
  }
}

def resolveBuildUrl() {
  def raw = (env.BUILD_URL ?: '').trim()
  def publicBase = (env.JENKINS_PUBLIC_URL ?: '').trim()
  if (!publicBase) {
    return raw
  }

  publicBase = publicBase.replaceAll('/+$', '')
  if (!raw) {
    return publicBase
  }

  def m = (raw =~ /^https?:\/\/[^\/]+(\/.*)?$/)
  if (!m) {
    return raw
  }
  def path = m[0][1] ?: '/'
  return "${publicBase}${path}"
}

def resolveCommitSubject() {
  def fromCaptured = (env.CI_COMMIT_SUBJECT ?: '').trim()
  if (fromCaptured) {
    return fromCaptured
  }

  def fromEnv = (env.GIT_COMMIT_MESSAGE ?: '').trim()
  if (fromEnv) {
    return fromEnv
  }

  try {
    def subject = sh(
      script: "git show -s --format=%s HEAD 2>/dev/null || true",
      returnStdout: true
    ).trim()
    return subject ?: 'n/a'
  } catch (Exception ignored) {
    return 'n/a'
  }
}

def notifyTelegram(String text) {
  def tokenCredId = env.TELEGRAM_BOT_TOKEN_CREDENTIALS_ID ?: 'telegram-bot-token'
  def chatCredId = env.TELEGRAM_CHAT_ID_CREDENTIALS_ID ?: 'telegram-chat-id'

  try {
    withCredentials([
      string(credentialsId: tokenCredId, variable: 'TG_TOKEN'),
      string(credentialsId: chatCredId, variable: 'TG_CHAT_ID')
    ]) {
      sh """
        set -euo pipefail
        curl -fsS -X POST "https://api.telegram.org/bot\${TG_TOKEN}/sendMessage" \\
          -d "chat_id=\${TG_CHAT_ID}" \\
          --data-urlencode "text=${text}" >/dev/null
      """
    }
  } catch (Exception e) {
    echo "Skipping Telegram notification: ${e.getMessage()}"
  }
}

def buildTelegramMessage(String status, String summary) {
  def branch = (env.BRANCH_NAME ?: 'n/a').trim()
  def job = (env.JOB_NAME ?: 'n/a').trim()
  def buildNo = (env.BUILD_NUMBER ?: 'n/a').trim()
  def sha = (env.GIT_COMMIT ?: '').trim()
  def shortSha = sha ? sha.take(7) : 'n/a'
  def subject = resolveCommitSubject()

  return """\
Jenkins CI: ${status}
Summary: ${summary}
Job: ${job}
Branch: ${branch}
Build: #${buildNo}
Commit: ${shortSha}
Message: ${subject}
""".stripIndent().trim()
}

pipeline {
  agent any

  triggers {
    githubPush()
  }

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30'))
    // Prevent duplicate rebuilds from Multibranch indexing (e.g. after Jenkins restart).
    overrideIndexTriggers(false)
  }

  environment {
    PIP_DISABLE_PIP_VERSION_CHECK = '1'
    PYTHONUNBUFFERED = '1'
    COMPOSE_DOCKER_CLI_BUILD = '1'
    DOCKER_BUILDKIT = '1'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.CI_COMMIT_SUBJECT = sh(
            script: "git show -s --format=%s HEAD 2>/dev/null || true",
            returnStdout: true
          ).trim()
        }
      }
    }

    stage('Set GitHub Status: pending') {
      steps {
        script {
          setGithubStatus('pending', 'Jenkins pipeline is running')
        }
      }
    }

    stage('Prepare CI Environment') {
      steps {
        sh '''
          set -euxo pipefail
          cp .env.example .env
          mkdir -p secrets certs reports
          printf 'dummy-password' > secrets/postgres_password.txt
          printf 'dummy-password' > secrets/grafana_admin_password.txt
          printf 'dummy-cert' > certs/nginx-selfsigned.crt
          printf 'dummy-key' > certs/nginx-selfsigned.key
        '''
      }
    }

    stage('Validate Compose') {
      steps {
        sh '''
          set -euxo pipefail
          docker compose -f docker-compose.yml --env-file .env.example config > reports/compose.validated.yml
        '''
      }
    }

    stage('Autotests') {
      steps {
        sh '''
          set -euxo pipefail
          JOB_SAFE="$(echo "${JOB_NAME:-job}" | tr '/:% @' '_____')"
          TEST_CONTAINER="my-app-tests-${JOB_SAFE}-${BUILD_NUMBER:-local}"
          docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
          docker create --name "$TEST_CONTAINER" -w /work python:3.10-slim bash -lc "
            python -m pip install --upgrade pip &&
            pip install -r api/requirements.txt -r worker/requirements.txt pytest pytest-cov &&
            pytest -q api/tests worker/tests \
              --junitxml=reports/pytest.xml \
              --cov=api --cov=worker \
              --cov-report=term \
              --cov-report=xml:reports/coverage.xml
          " >/dev/null
          docker cp . "$TEST_CONTAINER":/work
          if ! docker start -a "$TEST_CONTAINER"; then
            docker cp "$TEST_CONTAINER":/work/reports/. reports/ || true
            docker rm -f "$TEST_CONTAINER" || true
            exit 1
          fi
          docker cp "$TEST_CONTAINER":/work/reports/. reports/
          docker rm -f "$TEST_CONTAINER"
        '''
      }
      post {
        always {
          junit testResults: 'reports/pytest.xml', allowEmptyResults: true
        }
      }
    }

    stage('Build Docker Images') {
      steps {
        sh '''
          set -euxo pipefail
          export DOCKER_BUILDKIT=0
          IMAGE_TAG="ci-${BUILD_NUMBER:-local}"
          docker build -t "my-app/api:${IMAGE_TAG}" ./api
          docker build -t "my-app/worker:${IMAGE_TAG}" ./worker
          docker build -t "my-app/frontend:${IMAGE_TAG}" ./frontend
        '''
      }
    }

    stage('Security Scan (Trivy)') {
      steps {
        sh '''
          set -euxo pipefail
          mkdir -p reports/trivy .trivycache
          TRIVY_IMAGE="aquasec/trivy:0.58.1"
          IMAGE_TAG="ci-${BUILD_NUMBER:-local}"
          SERVICES="api worker frontend"
          FAILED=0

          for SVC in $SERVICES; do
            IMAGE_REF="my-app/${SVC}:${IMAGE_TAG}"
            if ! docker image inspect "$IMAGE_REF" >/dev/null 2>&1; then
              echo "Built image not found: $IMAGE_REF"
              FAILED=1
              continue
            fi

            docker run --rm \
              -v /var/run/docker.sock:/var/run/docker.sock \
              -v "$PWD/reports:/reports" \
              -v "$PWD/.trivycache:/root/.cache" \
              "$TRIVY_IMAGE" image \
              --severity HIGH,CRITICAL \
              --format json \
              --output "/reports/trivy-${SVC}.json" \
              --exit-code 0 \
              "$IMAGE_REF"

            docker run --rm \
              -v /var/run/docker.sock:/var/run/docker.sock \
              -v "$PWD/reports:/reports" \
              -v "$PWD/.trivycache:/root/.cache" \
              "$TRIVY_IMAGE" image \
              --severity HIGH,CRITICAL \
              --format sarif \
              --output "/reports/trivy-${SVC}.sarif" \
              --exit-code 0 \
              "$IMAGE_REF"

            if ! docker run --rm \
              -v /var/run/docker.sock:/var/run/docker.sock \
              -v "$PWD/.trivycache:/root/.cache" \
              "$TRIVY_IMAGE" image \
              --severity HIGH,CRITICAL \
              --exit-code 1 \
              "$IMAGE_REF" > "reports/trivy-${SVC}.txt"; then
              echo "Trivy gate failed for $SVC (HIGH/CRITICAL found)"
              FAILED=1
            fi
          done

          test "$FAILED" -eq 0
        '''
      }
    }
  }

  post {
    success {
      script {
        setGithubStatus('success', 'Jenkins pipeline passed')
        notifyTelegram(buildTelegramMessage('SUCCESS', 'All stages passed'))
      }
    }
    failure {
      script {
        setGithubStatus('failure', 'Jenkins pipeline failed')
        notifyTelegram(buildTelegramMessage('FAILURE', 'Pipeline failed. Check build log'))
      }
    }
    aborted {
      script {
        setGithubStatus('error', 'Jenkins pipeline was aborted')
        notifyTelegram(buildTelegramMessage('ABORTED', 'Build was aborted'))
      }
    }
    unstable {
      script {
        setGithubStatus('failure', 'Jenkins pipeline is unstable')
        notifyTelegram(buildTelegramMessage('UNSTABLE', 'Build unstable. Inspect test reports'))
      }
    }
    always {
      archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
      deleteDir()
    }
  }
}
