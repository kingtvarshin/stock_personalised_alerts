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
    string(name: 'BRANCH_NAME', defaultValue: 'feature/pdf_output_for_summary', description: 'Branch to checkout and run')
    string(name: 'IMAGE_NAME', defaultValue: 'stock-analyzer', description: 'Docker image name')
    booleanParam(name: 'DRY_RUN', defaultValue: false, description: 'Run pipeline with --dry-run (no emails sent)')
    file(name: 'EXCEL_FILE', description: 'Optional Excel file upload for this run. It will be copied to src/resources and used without committing it to git.')
  }

  environment {
    APP_DIR          = 'src'
    IMAGE_NAME       = "${params.IMAGE_NAME}"
    DRY_RUN          = "${params.DRY_RUN}"
    SSH_CREDS_ID     = 'truenas-ssh-creds'
    REMOTE_CACHE_DIR = '/tmp/stock-personalised-alerts-cache'
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

    stage('Prepare Excel Input') {
      steps {
        script {
          env.UPLOADED_EXCEL_NAME = sh(
            script: 'if [ -n "${EXCEL_FILE:-}" ] && [ -f "$EXCEL_FILE" ]; then basename "$EXCEL_FILE"; fi',
            returnStdout: true
          ).trim()
          env.HAS_EXCEL_UPLOAD = env.UPLOADED_EXCEL_NAME ? 'true' : 'false'

          sh '''#!/bin/bash
            set -euo pipefail
            mkdir -p "$APP_DIR/resources"

            if [ -n "${EXCEL_FILE:-}" ] && [ -f "$EXCEL_FILE" ]; then
              excel_basename="$(basename "$EXCEL_FILE")"
              cp "$EXCEL_FILE" "$APP_DIR/resources/$excel_basename"
              echo "[excel-input] Uploaded Excel file prepared: $excel_basename"
            else
              echo "[excel-input] No Excel file uploaded. NEW_EXCEL_FLAG will be set dynamically at runtime."
            fi
          '''
        }
      }
    }

    // ---------------------------------------------------------------
    stage('Fix Docker Socket') {
    // ---------------------------------------------------------------
    // Checks Docker access on the TrueNAS host over SSH. If docker info
    // fails there, it fixes /var/run/docker.sock permissions remotely.
    // ---------------------------------------------------------------
      steps {
        script {
          if (!env.TRUENAS_REGISTRY_HOST?.trim()) {
            error('TRUENAS_REGISTRY_HOST is not set in Jenkins environment variables')
          }
          env.TRUENAS_SSH_HOST = env.TRUENAS_REGISTRY_HOST.split(':')[0]

          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            sh """
              set -euo pipefail
              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  'if docker info >/dev/null 2>&1; then
                     echo "[fix-socket] Docker socket is accessible - no action needed"
                   else
                     echo "[fix-socket] Docker socket not accessible - fixing permissions via SSH"
                     chmod 666 /var/run/docker.sock
                     echo "[fix-socket] chmod applied OK"
                   fi'
            """
          }
        }
      }
    }

    stage('Sync Workspace To Docker Host') {
      steps {
        script {
          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            env.REMOTE_DIR = "/tmp/stock-personalised-alerts-${BUILD_NUMBER}"
            sh """
              set -euo pipefail

              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "rm -rf '${env.REMOTE_DIR}' && mkdir -p '${env.REMOTE_DIR}'"

              tar --exclude=.git -czf - . | ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "tar -xzf - -C '${env.REMOTE_DIR}'"
            """
          }
        }
      }
    }

    stage('Restore Cached Inputs') {
      steps {
        script {
          if (env.HAS_EXCEL_UPLOAD != 'true') {
            withCredentials([sshUserPrivateKey(
              credentialsId: env.SSH_CREDS_ID,
              keyFileVariable: 'SSH_KEY_FILE',
              usernameVariable: 'SSH_USER_FROM_CRED'
            )]) {
              sh """
                set -euo pipefail
                ssh -i "\$SSH_KEY_FILE" \\
                    -o StrictHostKeyChecking=no \\
                    -o BatchMode=yes \\
                    "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                    "mkdir -p '${env.REMOTE_CACHE_DIR}'; \
                     if [ -f '${env.REMOTE_CACHE_DIR}/stocksdict.json' ]; then \
                       cp '${env.REMOTE_CACHE_DIR}/stocksdict.json' '${env.REMOTE_DIR}/$APP_DIR/stocksdict.json' && \
                       echo '[cache] Restored stocksdict.json from cache'; \
                     else \
                       echo '[cache] stocksdict.json not found in cache'; \
                       exit 42; \
                     fi"
              """
            }
          } else {
            echo '[cache] Excel uploaded for this run; cache restore skipped.'
          }
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        script {
          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            sh """
              set -euo pipefail
              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "cd '${env.REMOTE_DIR}/$APP_DIR' && docker build -t '$IMAGE_NAME:$BUILD_NUMBER' -t '$IMAGE_NAME:latest' ."
            """
          }
        }
      }
    }

    stage('Run Script') {
      steps {
        script {
          def remoteRunCmd = (DRY_RUN == 'true') ? 'python3 main.py --dry-run' : 'python3 main.py'
          def excelEnvArgs = (env.HAS_EXCEL_UPLOAD == 'true')
            ? "-e NEW_EXCEL_FLAG=True -e EXCEL_NAME=${env.UPLOADED_EXCEL_NAME}"
            : "-e NEW_EXCEL_FLAG=False"

          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            sh """
              set -euo pipefail

              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "cd '${env.REMOTE_DIR}/$APP_DIR' && docker run --rm --env-file .env ${excelEnvArgs} -v '${env.REMOTE_DIR}/$APP_DIR:/app' '$IMAGE_NAME:$BUILD_NUMBER' ${remoteRunCmd}"
            """
          }
        }
      }
    }

    stage('Persist Generated Files') {
      steps {
        script {
          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            sh """
              set -euo pipefail
              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "mkdir -p '${env.REMOTE_CACHE_DIR}'; \
                   [ -f '${env.REMOTE_DIR}/$APP_DIR/stocksdict.json' ] && cp '${env.REMOTE_DIR}/$APP_DIR/stocksdict.json' '${env.REMOTE_CACHE_DIR}/stocksdict.json' || true; \
                   [ -f '${env.REMOTE_DIR}/$APP_DIR/fiftytwo_weeks_analysis.json' ] && cp '${env.REMOTE_DIR}/$APP_DIR/fiftytwo_weeks_analysis.json' '${env.REMOTE_CACHE_DIR}/fiftytwo_weeks_analysis.json' || true; \
                   [ -f '${env.REMOTE_DIR}/$APP_DIR/time_analysis.json' ] && cp '${env.REMOTE_DIR}/$APP_DIR/time_analysis.json' '${env.REMOTE_CACHE_DIR}/time_analysis.json' || true; \
                   [ -f '${env.REMOTE_DIR}/$APP_DIR/indicators_data.csv' ] && cp '${env.REMOTE_DIR}/$APP_DIR/indicators_data.csv' '${env.REMOTE_CACHE_DIR}/indicators_data.csv' || true"
            """
          }
        }
      }
    }
  }

  post {
    always {
      sh '''#!/bin/bash
        set +e
        rm -f "$APP_DIR/.env"
      '''
      script {
        if (env.REMOTE_DIR) {
          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            sh """
              set +e
              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "rm -rf '${env.REMOTE_DIR}'"
            """
          }
        }
      }
      archiveArtifacts artifacts: 'src/*.csv,src/*.json', allowEmptyArchive: true
    }
  }
}
