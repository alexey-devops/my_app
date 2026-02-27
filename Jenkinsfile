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

    stage('Prepare CI Environment') {
      steps {
        sh '''
          set -euxo pipefail
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          pip install -r api/requirements.txt -r worker/requirements.txt pytest pytest-cov

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
          . .venv/bin/activate
          pytest -q api/tests worker/tests \
            --junitxml=reports/pytest.xml \
            --cov=api --cov=worker \
            --cov-report=term \
            --cov-report=xml:reports/coverage.xml
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
    always {
      archiveArtifacts artifacts: 'reports/*', allowEmptyArchive: true
      deleteDir()
    }
  }
}
