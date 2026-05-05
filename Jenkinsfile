pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  triggers {
    // Weekdays at a stable hashed minute around 08:00 Jenkins controller time
    cron('H 8 * * 1-5')
  }

  parameters {
    string(name: 'REPO_URL', defaultValue: '', description: 'Git repository URL. Leave empty to use GIT_URL from job SCM.')
    string(name: 'BRANCH_NAME', defaultValue: 'main', description: 'Branch to checkout and run')
    string(name: 'GIT_CREDENTIALS_ID', defaultValue: '', description: 'Optional Jenkins credentials ID for private repo access')

    booleanParam(name: 'USE_JENKINS_SECRET_ENV', defaultValue: true, description: 'Use Jenkins Secret File credential as src/.env')
    string(name: 'ENV_FILE_CREDENTIAL_ID', defaultValue: 'stock-alert-env-file', description: 'Jenkins Secret File credentials ID containing .env content')
    text(name: 'ENV_FILE_CONTENT', defaultValue: '', description: 'Used only when USE_JENKINS_SECRET_ENV=false. Paste .env content here.')

    string(name: 'IMAGE_NAME', defaultValue: 'stock-analyzer', description: 'Docker image name')
    booleanParam(name: 'DRY_RUN', defaultValue: false, description: 'Run pipeline with --dry-run (no emails sent)')
  }

  environment {
    APP_DIR = 'src'
  }

  stages {
    stage('Checkout') {
      steps {
        script {
          def repoUrl = params.REPO_URL?.trim() ? params.REPO_URL.trim() : (env.GIT_URL ?: '')
          if (!repoUrl) {
            error('No repository URL found. Set REPO_URL parameter or configure SCM in Jenkins job.')
          }

          def remoteConfig = [url: repoUrl]
          if (params.GIT_CREDENTIALS_ID?.trim()) {
            remoteConfig.credentialsId = params.GIT_CREDENTIALS_ID.trim()
          }

          checkout([
            $class: 'GitSCM',
            branches: [[name: "*/${params.BRANCH_NAME}"]],
            userRemoteConfigs: [remoteConfig],
            extensions: [[$class: 'CleanBeforeCheckout']]
          ])
        }
      }
    }

    stage('Prepare .env') {
      steps {
        script {
          if (params.USE_JENKINS_SECRET_ENV) {
            withCredentials([file(credentialsId: params.ENV_FILE_CREDENTIAL_ID, variable: 'ENV_FILE_SECRET')]) {
              sh '''#!/bin/bash
                set -euo pipefail
                cp "$ENV_FILE_SECRET" "$APP_DIR/.env"
                chmod 600 "$APP_DIR/.env"
              '''
            }
          } else {
            if (!params.ENV_FILE_CONTENT?.trim()) {
              error('ENV_FILE_CONTENT is empty while USE_JENKINS_SECRET_ENV=false')
            }
            writeFile file: "${env.APP_DIR}/.env", text: params.ENV_FILE_CONTENT
          }
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        sh '''#!/bin/bash
          set -euo pipefail
          cd "$APP_DIR"
          docker build -t "$IMAGE_NAME:$BUILD_NUMBER" -t "$IMAGE_NAME:latest" .
        '''
      }
    }

    stage('Run Script') {
      steps {
        sh '''#!/bin/bash
          set -euo pipefail
          cd "$APP_DIR"
          if [ "$DRY_RUN" = "true" ]; then
            docker run --rm --env-file .env "$IMAGE_NAME:$BUILD_NUMBER" python3 main.py --dry-run
          else
            docker run --rm --env-file .env "$IMAGE_NAME:$BUILD_NUMBER" python3 main.py
          fi
        '''
      }
    }
  }

  post {
    always {
      sh '''#!/bin/bash
        set +e
        rm -f "$APP_DIR/.env"
      '''
      archiveArtifacts artifacts: 'src/*.csv,src/*.json', allowEmptyArchive: true
    }
  }
}
