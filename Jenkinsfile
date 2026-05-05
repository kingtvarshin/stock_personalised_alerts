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
    string(name: 'BRANCH_NAME', defaultValue: 'main', description: 'Branch to checkout and run')
    string(name: 'IMAGE_NAME', defaultValue: 'stock-analyzer', description: 'Docker image name')
    booleanParam(name: 'DRY_RUN', defaultValue: false, description: 'Run pipeline with --dry-run (no emails sent)')
  }

  environment {
    APP_DIR          = 'src'
    IMAGE_NAME       = "${params.IMAGE_NAME}"
    DRY_RUN          = "${params.DRY_RUN}"
    SSH_CREDS_ID     = 'truenas-ssh-creds'
    // REGISTRY_HOST is injected by Jenkins (Manage Jenkins → System → Global properties → Environment variables)
  }

  stages {
    stage('Checkout') {
      steps {
        checkout([
          $class: 'GitSCM',
          branches: [[name: "*/${params.BRANCH_NAME}"]],
          userRemoteConfigs: scm.userRemoteConfigs,
          extensions: [[$class: 'CleanBeforeCheckout']]
        ])
      }
    }

    stage('Prepare .env') {
      steps {
        withCredentials([file(credentialsId: 'stock-alert-env-file', variable: 'ENV_FILE_SECRET')]) {
          sh '''#!/bin/bash
            set -euo pipefail
            cp "$ENV_FILE_SECRET" "$APP_DIR/.env"
            chmod 600 "$APP_DIR/.env"
          '''
        }
      }
    }

    // ---------------------------------------------------------------
    stage('Fix Docker Socket') {
    // ---------------------------------------------------------------
    // Checks if /var/run/docker.sock is world-readable. If not (i.e.
    // permission denied), SSHes into TrueNAS and fixes it. No-ops on
    // every build where the socket is already accessible.
    // ---------------------------------------------------------------
    // ---------------------------------------------------------------
    // Locates the Docker CLI binary (it may not be on PATH but present
    // at a known system path). Then checks if the socket is accessible.
    // If permission is denied, SSHes into TrueNAS to chmod it. No-ops
    // when Docker is already working.
    // ---------------------------------------------------------------
      steps {
        script {
          env.TRUENAS_SSH_HOST = env.TRUENAS_REGISTRY_HOST.split(':')[0]

          // Resolve docker binary — fall back to known system paths if not on PATH
          env.DOCKER_CMD = sh(
            script: 'command -v docker 2>/dev/null || ls /usr/bin/docker /usr/local/bin/docker 2>/dev/null | head -1 || echo ""',
            returnStdout: true
          ).trim()

          if (!env.DOCKER_CMD) {
            error('[fix-socket] Docker CLI not found. Install docker-ce-cli in the Jenkins container.')
          }
          echo "[fix-socket] Found Docker CLI at: ${env.DOCKER_CMD}"

          def exitCode = sh(
            script: "${env.DOCKER_CMD} info > /dev/null 2>&1",
            returnStatus: true
          )

          if (exitCode == 0) {
            echo '[fix-socket] Docker socket is accessible — no action needed'
          } else {
            echo '[fix-socket] Docker socket not accessible — fixing permissions via SSH'
            withCredentials([sshUserPrivateKey(
              credentialsId: env.SSH_CREDS_ID,
              keyFileVariable: 'SSH_KEY_FILE',
              usernameVariable: 'SSH_USER_FROM_CRED'
            )]) {
              sh """
                ssh -i "\$SSH_KEY_FILE" \\
                    -o StrictHostKeyChecking=no \\
                    -o BatchMode=yes \\
                    "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                    'chmod 666 /var/run/docker.sock && echo "[fix-socket] chmod applied OK"'
              """
            }
          }
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        sh '''
          set -euo pipefail
          cd "$APP_DIR"
          "$DOCKER_CMD" build -t "$IMAGE_NAME:$BUILD_NUMBER" -t "$IMAGE_NAME:latest" .
        '''
      }
    }

    stage('Run Script') {
      steps {
        sh '''
          set -euo pipefail
          cd "$APP_DIR"
          if [ "$DRY_RUN" = "true" ]; then
            "$DOCKER_CMD" run --rm --env-file .env "$IMAGE_NAME:$BUILD_NUMBER" python3 main.py --dry-run
          else
            "$DOCKER_CMD" run --rm --env-file .env "$IMAGE_NAME:$BUILD_NUMBER" python3 main.py
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
