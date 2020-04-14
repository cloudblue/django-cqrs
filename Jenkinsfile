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
      image: python:3.8.0-buster
      imagePullPolicy: IfNotPresent
      command:
        - cat
      tty: true
      resources:
        requests:
          memory: "1Gi"
          cpu: '1'
    - name: sonar-scanner
      image: sonarsource/sonar-scanner-cli:4.2
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
          version = sh(script: 'python setup.py --version', returnStdout: true).trim()
          echo "Building version: ${version}"
          currentBuild.displayName = "${version}"
          projectVersion = version.tokenize('.')[0]
        }
      }
    }
    stage('Install deps') {
      steps {
        container('python') {
          sh 'pip install flake8'
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
          withCredentials([usernamePassword(credentialsId: 'connect-ci-artifactory', usernameVariable: 'TWINE_USERNAME', passwordVariable: 'TWINE_PASSWORD')]) {
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
            -Dsonar.pullrequest.key=${env.CHANGE_ID} \
            -Dsonar.pullrequest.branch=${env.CHANGE_BRANCH} \
            -Dsonar.pullrequest.base=${env.CHANGE_TARGET} \
            -Dsonar.pullrequest.bitbucketserver.headSha=${env.GIT_COMMIT}
          """
        }
      }
    }
    stage('Scan and push to Sonar') {
      when { not { changeRequest() } }
      steps {
        container('sonar-scanner') {
          sh """sonar-scanner \
            -Dsonar.projectVersion=${version}"""
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