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
          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            sh """
              set -euo pipefail
              REMOTE_RUN_CMD="${DRY_RUN == 'true' ? 'python3 main.py --dry-run' : 'python3 main.py'}"

              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "cd '${env.REMOTE_DIR}/$APP_DIR' && docker run --rm --env-file .env '$IMAGE_NAME:$BUILD_NUMBER' \$REMOTE_RUN_CMD"
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
        if (fileExists('.remote_dir')) {
          withCredentials([sshUserPrivateKey(
            credentialsId: env.SSH_CREDS_ID,
            keyFileVariable: 'SSH_KEY_FILE',
            usernameVariable: 'SSH_USER_FROM_CRED'
          )]) {
            sh """
              set +e
              REMOTE_DIR=\$(cat .remote_dir)
              ssh -i "\$SSH_KEY_FILE" \\
                  -o StrictHostKeyChecking=no \\
                  -o BatchMode=yes \\
                  "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                  "rm -rf '\$REMOTE_DIR'"
              rm -f .remote_dir
            """
          }
        }
      }
      archiveArtifacts artifacts: 'src/*.csv,src/*.json', allowEmptyArchive: true
    }
  }
}
