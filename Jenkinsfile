pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = 'bibliotheque'
        DOCKER_REGISTRY       = 'registry.dit.sn'
        IMAGE_TAG             = "${env.BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Recuperation du code source...'
                checkout scm
            }
        }

        stage('Lint & Validation') {
            parallel {
                stage('Python Lint') {
                    steps {
                        sh '''
                            pip install flake8 --quiet
                            flake8 services/ ml/ --max-line-length=120 --ignore=E501,W503 || true
                        '''
                    }
                }
                stage('Docker Compose Validate') {
                    steps {
                        sh 'docker compose config --quiet'
                    }
                }
                stage('DVC Validate') {
                    steps {
                        sh '''
                            pip install dvc --quiet
                            dvc check-ignore -v . || true
                        '''
                    }
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Construction des images Docker...'
                sh 'docker compose build --no-cache'
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Lancement des tests d integration...'
                sh '''
                    docker compose --profile dev up -d db
                    sleep 10
                    docker compose --profile dev up -d livres utilisateurs emprunts recommandation

                    # Test de sante des services
                    sleep 15
                    curl -f http://localhost:5001/health || exit 1
                    curl -f http://localhost:5002/health || exit 1
                    curl -f http://localhost:5003/health || exit 1
                    curl -f http://localhost:8000/health || exit 1

                    echo "Tous les services sont operationnels"
                '''
            }
            post {
                always {
                    sh 'docker compose --profile dev down -v || true'
                }
            }
        }

        stage('DVC Pipeline') {
            when {
                anyOf {
                    branch 'master'
                    branch 'main'
                    changeset 'data/**'
                    changeset 'ml/**'
                    changeset 'params.yaml'
                }
            }
            steps {
                echo 'Execution du pipeline DVC...'
                withCredentials([string(credentialsId: 'gdrive-token', variable: 'GDRIVE_TOKEN')]) {
                    sh '''
                        pip install dvc dvc-gdrive scikit-learn scipy pandas numpy --quiet
                        dvc pull || true
                        dvc repro
                        dvc metrics show
                    '''
                }
            }
            post {
                success {
                    sh 'dvc push || true'
                    archiveArtifacts artifacts: 'metrics.json', fingerprint: true
                }
            }
        }

        stage('Push to Registry') {
            when {
                branch 'master'
            }
            steps {
                echo 'Push des images vers le registry...'
                withCredentials([usernamePassword(
                    credentialsId: 'docker-registry-credentials',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASS'
                )]) {
                    sh '''
                        echo $REGISTRY_PASS | docker login $DOCKER_REGISTRY -u $REGISTRY_USER --password-stdin
                        docker tag bibliotheque-livres $DOCKER_REGISTRY/bibliotheque/livres:$IMAGE_TAG
                        docker tag bibliotheque-utilisateurs $DOCKER_REGISTRY/bibliotheque/utilisateurs:$IMAGE_TAG
                        docker tag bibliotheque-emprunts $DOCKER_REGISTRY/bibliotheque/emprunts:$IMAGE_TAG
                        docker tag bibliotheque-recommandation $DOCKER_REGISTRY/bibliotheque/recommandation:$IMAGE_TAG
                        docker tag bibliotheque-frontend $DOCKER_REGISTRY/bibliotheque/frontend:$IMAGE_TAG
                        docker push $DOCKER_REGISTRY/bibliotheque/livres:$IMAGE_TAG
                        docker push $DOCKER_REGISTRY/bibliotheque/utilisateurs:$IMAGE_TAG
                        docker push $DOCKER_REGISTRY/bibliotheque/emprunts:$IMAGE_TAG
                        docker push $DOCKER_REGISTRY/bibliotheque/recommandation:$IMAGE_TAG
                        docker push $DOCKER_REGISTRY/bibliotheque/frontend:$IMAGE_TAG
                    '''
                }
            }
        }

        stage('Deploy Production') {
            when {
                branch 'master'
            }
            steps {
                echo 'Deploiement en production...'
                sh 'docker compose --profile prod up -d'
                echo 'Deploiement termine. Application disponible sur http://localhost'
            }
        }
    }

    post {
        success {
            echo "Pipeline reussi - Build #${env.BUILD_NUMBER}"
        }
        failure {
            echo "Pipeline echoue - Build #${env.BUILD_NUMBER}"
            sh 'docker compose down -v || true'
        }
        always {
            cleanWs()
        }
    }
}
