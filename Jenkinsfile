// Build and test common-model-mixins Python package.
library 'connect-common'

pipeline {
  options {
    buildDiscarder(logRotator(numToKeepStr: '100', artifactNumToKeepStr: '30'))
    timeout(time: 30, unit: 'MINUTES')
  }
  agent {
    kubernetes {
      defaultContainer 'python'
      yaml """
kind: Pod
spec:
  containers:
    - name: python
      image: python:2.7.16-stretch
      imagePullPolicy: IfNotPresent
      command:
        - cat
      tty: true
      resources:
        requests:
          memory: "1Gi"
          cpu: '1'
    - name: sonar-scanner
      image: cloud.repo.int.zone/sonar-scanner:2.6.1
      imagePullPolicy: IfNotPresent
      command:
        - cat
      tty: true
"""
    }
  }
  stages {
    stage('Init') {
      steps {
        script {
          version = sh(script: 'git describe --always --abbrev=7', returnStdout: true).trim()
          echo "Building version: ${version}"
          currentBuild.displayName = "${version}"
          projectVersion = version.tokenize('.')[0]
        }
      }
    }
    stage('Install deps') {
      steps {
        container('python') {
          sh 'pip install -U pip'
          sh """pip install --index-url=\"https://repo.int.zone/artifactory/api/pypi/pypi/simple\" \
                -r requirements/dev.txt \
                -r requirements/test.txt"""
        }
      }
    }
    stage('Test') {
      steps {
        container('python') {
          sh 'flake8'
          sh 'python setup.py test'
        }
      }
    }
    stage('Upload') {
      when { not { changeRequest() } }
      steps {
        container('python') {
          sh 'pip install -U twine'
          sh 'git clean -fdx'
          withCredentials([usernamePassword(credentialsId: 'connect-artifactory', usernameVariable: 'TWINE_USERNAME', passwordVariable: 'TWINE_PASSWORD')]) {
            sh 'python setup.py sdist'
            sh 'twine upload --repository-url https://repo.int.zone/artifactory/api/pypi/pypi-local dist/*'
          }
        }
      }
    }
    stage('Scan') {
      when { changeRequest() }
      steps {
        container('sonar-scanner') {
          sh """sonar-scanner \
            -Dsonar.projectVersion=${projectVersion} \
            -Dsonar.stash.project=SWFT \
            -Dsonar.stash.repository=django-cqrs \
            -Dsonar.stash.pullrequest.id=${env.CHANGE_ID} \
            -Dsonar.stash.notification=true \
            -Dsonar.stash.comments.reset=false \
            -Dsonar.stash.login=commit-blocker-bot \
            -Dsonar.stash.report.issues=true \
            -Dsonar.stash.report.line=false \
            -Dsonar.stash.report.coverage=false"""
        }
      }
    }
    stage('Scan and push to Sonar') {
      when { not { changeRequest() } }
      steps {
        container('sonar-scanner') {
          sh """sonar-scanner \
            -Dsonar.projectVersion=${projectVersion}"""
        }
      }
    }
  }
  post {
    always {
      script {
        currentBuild.result = currentBuild.result ?: 'SUCCESS'
        if (!env.BRANCH_NAME.startsWith('PR-')) {
          notifyTelegram chat_labels: ['connect-build']
        }
      }
    }
  }
}