def setGithubStatus(String state, String description) {
  def statusCredentialId = env.GITHUB_STATUS_CREDENTIALS_ID ?: 'my-app'
  def publishWithTokenHeader = {
    sh """
      set -euo pipefail
      REMOTE_URL=\$(git config --get remote.origin.url)
      case "\$REMOTE_URL" in
        git@github.com:*) REPO="\${REMOTE_URL#git@github.com:}" ;;
        https://github.com/*) REPO="\${REMOTE_URL#https://github.com/}" ;;
        *)
          echo "Skipping GitHub status update for unsupported remote: \$REMOTE_URL"
          exit 0
          ;;
      esac
      REPO="\${REPO%.git}"
      SHA=\$(git rev-parse HEAD)
      cat > /tmp/github-status.json <<JSON
{"state":"${state}","context":"ci/jenkins","description":"${description}","target_url":"${env.BUILD_URL ?: ''}"}
JSON
      curl -fsS -X POST \\
        -H "Authorization: token \$GITHUB_TOKEN" \\
        -H "Accept: application/vnd.github+json" \\
        "https://api.github.com/repos/\$REPO/statuses/\$SHA" \\
        -d @/tmp/github-status.json >/dev/null
    """
  }

  def publishWithBasicAuth = {
    sh """
      set -euo pipefail
      REMOTE_URL=\$(git config --get remote.origin.url)
      case "\$REMOTE_URL" in
        git@github.com:*) REPO="\${REMOTE_URL#git@github.com:}" ;;
        https://github.com/*) REPO="\${REMOTE_URL#https://github.com/}" ;;
        *)
          echo "Skipping GitHub status update for unsupported remote: \$REMOTE_URL"
          exit 0
          ;;
      esac
      REPO="\${REPO%.git}"
      SHA=\$(git rev-parse HEAD)
      cat > /tmp/github-status.json <<JSON
{"state":"${state}","context":"ci/jenkins","description":"${description}","target_url":"${env.BUILD_URL ?: ''}"}
JSON
      curl -fsS -X POST \\
        -u "\$GITHUB_USER:\$GITHUB_TOKEN" \\
        -H "Accept: application/vnd.github+json" \\
        "https://api.github.com/repos/\$REPO/statuses/\$SHA" \\
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

pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  triggers {
    githubPush()
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
          TEST_CONTAINER="my-app-tests-${BUILD_NUMBER:-local}"
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
          docker compose build api worker frontend
        '''
      }
    }
  }

  post {
    success {
      script {
        setGithubStatus('success', 'Jenkins pipeline passed')
      }
    }
    failure {
      script {
        setGithubStatus('failure', 'Jenkins pipeline failed')
      }
    }
    aborted {
      script {
        setGithubStatus('error', 'Jenkins pipeline was aborted')
      }
    }
    unstable {
      script {
        setGithubStatus('failure', 'Jenkins pipeline is unstable')
      }
    }
    always {
      archiveArtifacts artifacts: 'reports/*', allowEmptyArchive: true
      deleteDir()
    }
  }
}
