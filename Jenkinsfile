pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
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
          extensions: []
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
          // Some Jenkins setups expose file parameters as a path, others as filename only.
          // Keep the original parameter value and resolve the real file path in shell.
          env.EXCEL_PARAM_RAW = (params.EXCEL_FILE ?: '').trim()
          env.UPLOADED_EXCEL_NAME = ''
          env.HAS_EXCEL_UPLOAD = 'false'

          sh '''#!/bin/bash
            set -euo pipefail
            mkdir -p "$APP_DIR/resources"

            excel_src=""
            candidate_name=""

            # Prefer Jenkins-injected env var path when present
            if [ -n "${EXCEL_FILE:-}" ] && [ -f "$EXCEL_FILE" ]; then
              excel_src="$EXCEL_FILE"
            fi

            # If EXCEL_FILE is a basename (common Jenkins behavior), remember it for lookup.
            if [ -z "$excel_src" ] && [ -n "${EXCEL_FILE:-}" ]; then
              candidate_name="$(basename "$EXCEL_FILE")"
            fi

            # Fall back to params filename value (can be just basename)
            if [ -z "$excel_src" ] && [ -n "${EXCEL_PARAM_RAW:-}" ]; then
              if [ -f "$EXCEL_PARAM_RAW" ]; then
                excel_src="$EXCEL_PARAM_RAW"
              elif [ -f "$WORKSPACE/$EXCEL_PARAM_RAW" ]; then
                excel_src="$WORKSPACE/$EXCEL_PARAM_RAW"
              else
                found_path="$(find "$WORKSPACE" -maxdepth 3 -type f -name "$EXCEL_PARAM_RAW" 2>/dev/null | head -n 1 || true)"
                if [ -n "$found_path" ] && [ -f "$found_path" ]; then
                  excel_src="$found_path"
                fi
              fi
            fi

            # Search by candidate basename in common Jenkins locations.
            if [ -z "$excel_src" ] && [ -n "$candidate_name" ]; then
              if [ -f "$WORKSPACE/$candidate_name" ]; then
                excel_src="$WORKSPACE/$candidate_name"
              else
                found_path="$(find "$WORKSPACE" "$WORKSPACE@tmp" -maxdepth 5 -type f -name "$candidate_name" 2>/dev/null | head -n 1 || true)"
                if [ -n "$found_path" ] && [ -f "$found_path" ]; then
                  excel_src="$found_path"
                fi
              fi
            fi

            # Deterministic Jenkins file-parameter location (controller filesystem).
            # Path pattern: $JENKINS_HOME/jobs/<job path>/builds/<build #>/fileParameters/<parameter-name>
            # In most Jenkins setups, the stored file is named after the parameter key (EXCEL_FILE),
            # not the original uploaded filename.
            if [ -z "$excel_src" ] && [ -n "$candidate_name" ] && [ -n "${JENKINS_HOME:-}" ] && [ -n "${JOB_NAME:-}" ] && [ -n "${BUILD_NUMBER:-}" ]; then
              job_path="$(echo "$JOB_NAME" | sed 's#/#/jobs/#g')"
              fp_dir="$JENKINS_HOME/jobs/$job_path/builds/$BUILD_NUMBER/fileParameters"
              fp_by_param="$fp_dir/EXCEL_FILE"
              fp_by_name="$fp_dir/$candidate_name"

              if [ -f "$fp_by_param" ]; then
                excel_src="$fp_by_param"
                echo "[excel-input] Resolved from Jenkins fileParameters by parameter key: $fp_by_param"
              elif [ -f "$fp_by_name" ]; then
                excel_src="$fp_by_name"
                echo "[excel-input] Resolved from Jenkins fileParameters by filename: $fp_by_name"
              else
                echo "[excel-input] fileParameters dir checked: $fp_dir"
                ls -la "$fp_dir" 2>/dev/null || true
              fi
            fi

            # Final fallback: search common Jenkins temp/build locations without assuming
            # a specific storage layout for file parameters.
            if [ -z "$excel_src" ] && [ -n "$candidate_name" ]; then
              search_roots=""
              [ -n "${WORKSPACE:-}" ] && search_roots="$search_roots $WORKSPACE"
              [ -n "${WORKSPACE:-}" ] && [ -d "$WORKSPACE@tmp" ] && search_roots="$search_roots $WORKSPACE@tmp"

              if [ -n "${JENKINS_HOME:-}" ] && [ -n "${JOB_NAME:-}" ] && [ -n "${BUILD_NUMBER:-}" ]; then
                job_path="$(echo "$JOB_NAME" | sed 's#/#/jobs/#g')"
                build_dir="$JENKINS_HOME/jobs/$job_path/builds/$BUILD_NUMBER"
                [ -d "$build_dir" ] && search_roots="$search_roots $build_dir"
              fi

              if [ -n "$search_roots" ]; then
                found_path="$({
                  for root in $search_roots; do
                    [ -d "$root" ] || continue
                    find "$root" -maxdepth 8 -type f \( -name "$candidate_name" -o -name 'EXCEL_FILE' \) 2>/dev/null
                  done
                } | head -n 1 || true)"

                if [ -n "$found_path" ] && [ -f "$found_path" ]; then
                  excel_src="$found_path"
                  echo "[excel-input] Resolved from fallback search: $found_path"
                fi
              fi
            fi

            if [ -n "$excel_src" ] && [ -f "$excel_src" ]; then
              excel_basename="$(basename "$excel_src")"
              cp "$excel_src" "$APP_DIR/resources/$excel_basename"
              echo "UPLOADED_EXCEL_NAME=$excel_basename" > .excel_upload_meta
              echo "[excel-input] Uploaded Excel file prepared: $excel_basename"
              echo "[excel-input] Source file resolved at: $excel_src"
            else
              : > .excel_upload_meta
              echo "[excel-input] No valid Excel upload found."
              echo "[excel-input] EXCEL_FILE env: ${EXCEL_FILE:-<empty>}"
              echo "[excel-input] params.EXCEL_FILE: ${EXCEL_PARAM_RAW:-<empty>}"
              echo "[excel-input] WORKSPACE: ${WORKSPACE:-<empty>}"
              echo "[excel-input] WORKSPACE@tmp exists: $( [ -d "$WORKSPACE@tmp" ] && echo yes || echo no )"
              echo "[excel-input] JENKINS_HOME: ${JENKINS_HOME:-<empty>}"
              echo "[excel-input] JOB_NAME: ${JOB_NAME:-<empty>}"
              echo "[excel-input] BUILD_NUMBER: ${BUILD_NUMBER:-<empty>}"
              echo "[excel-input] NEW_EXCEL_FLAG will be set dynamically at runtime."
            fi
          '''

          def uploaded = sh(
            script: "grep '^UPLOADED_EXCEL_NAME=' .excel_upload_meta 2>/dev/null | cut -d= -f2- || true",
            returnStdout: true
          ).trim()
          env.UPLOADED_EXCEL_NAME = uploaded
          env.HAS_EXCEL_UPLOAD = uploaded ? 'true' : 'false'
          echo "[excel-input] HAS_EXCEL_UPLOAD=${env.HAS_EXCEL_UPLOAD}${uploaded ? ", UPLOADED_EXCEL_NAME=${uploaded}" : ''}"
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
              int restoreStatus = sh(
                script: """
                  set -euo pipefail
                  ssh -i "\$SSH_KEY_FILE" \\
                      -o StrictHostKeyChecking=no \\
                      -o BatchMode=yes \\
                      "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                      "mkdir -p '${env.REMOTE_CACHE_DIR}'; \
                       if [ -f '${env.REMOTE_DIR}/$APP_DIR/stocksdict.json' ]; then \
                         echo '[cache] Using stocksdict.json already present in workspace'; \
                       elif [ -f '${env.REMOTE_CACHE_DIR}/stocksdict.json' ]; then \
                         cp '${env.REMOTE_CACHE_DIR}/stocksdict.json' '${env.REMOTE_DIR}/$APP_DIR/stocksdict.json' && \
                         echo '[cache] Restored stocksdict.json from cache'; \
                       else \
                         echo '[cache] stocksdict.json not found in workspace or cache'; \
                         exit 3; \
                       fi"
                """,
                returnStatus: true
              )

              if (restoreStatus == 3) {
                def fallbackExcelName = sh(
                  script: """
                    set -euo pipefail
                    ssh -i "\$SSH_KEY_FILE" \\
                        -o StrictHostKeyChecking=no \\
                        -o BatchMode=yes \\
                        "\$SSH_USER_FROM_CRED@${env.TRUENAS_SSH_HOST}" \\
                        "find '${env.REMOTE_DIR}/$APP_DIR/resources' -maxdepth 1 -type f \\( -iname '*.xlsx' -o -iname '*.xls' \\) -printf '%T@ %f\\n' 2>/dev/null | sort -nr | sed -n '1s/^[^ ]* //p'"
                  """,
                  returnStdout: true
                ).trim()

                if (fallbackExcelName) {
                  env.HAS_EXCEL_UPLOAD = 'true'
                  env.UPLOADED_EXCEL_NAME = fallbackExcelName
                  restoreStatus = 0
                  echo "[cache] stocksdict.json missing in workspace/cache; bootstrapping from bundled Excel: ${fallbackExcelName}"
                } else {
                  error('No stocksdict.json available for non-Excel run, and no bundled Excel found under src/resources. Upload EXCEL_FILE once to bootstrap cache, then future non-Excel runs will succeed.')
                }
              }
              if (restoreStatus != 0) {
                error("Restore Cached Inputs failed with exit code ${restoreStatus}")
              }
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
