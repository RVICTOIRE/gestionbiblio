pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = 'bibliotheque'
        DOCKER_REGISTRY       = 'registry.dit.sn'
        IMAGE_TAG             = "${env.BUILD_NUMBER}"
        PATH                  = "/var/jenkins_home/.local/bin:${env.PATH}"
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
                            pip install flake8 --quiet --break-system-packages
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
                            pip install dvc --quiet --break-system-packages
                            dvc version
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

        stage('Unit Tests') {
            steps {
                echo 'Lancement des tests unitaires...'
                sh '''
                    pip install pytest --quiet --break-system-packages
                    pytest services/livres/test_health.py -v --tb=short || true
                    pytest services/utilisateurs/test_health.py -v --tb=short || true
                    pytest services/emprunts/test_health.py -v --tb=short || true
                    pytest services/recommandation/test_health.py -v --tb=short || true
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Lancement des tests d integration...'
                sh '''                    # Liberer le port 5432 si deja utilise
                    docker ps --filter "publish=5432" -q | xargs -r docker stop || true
                    docker compose --profile dev up -d db
                    echo "Attente de la base de donnees..."
                    for i in $(seq 1 12); do
                        docker compose exec -T db pg_isready -U postgres -d bibliotheque && break
                        sleep 5
                    done

                    docker compose --profile dev up -d livres utilisateurs emprunts recommandation

                    # Test de sante des services avec retry (60s max par service)
                    for SERVICE_URL in \
                        http://host.docker.internal:5001/health \
                        http://host.docker.internal:5002/health \
                        http://host.docker.internal:5003/health \
                        http://host.docker.internal:8000/health; do
                        echo "Attente de $SERVICE_URL..."
                        for i in $(seq 1 12); do
                            curl -sf $SERVICE_URL && break
                            [ $i -eq 12 ] && echo "TIMEOUT: $SERVICE_URL" && exit 1
                            sleep 5
                        done
                    done

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
                        pip install dvc dvc-gdrive scikit-learn scipy pandas numpy --quiet --break-system-packages
                        export GDRIVE_CREDENTIALS_DATA="$GDRIVE_TOKEN"
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

                        for SERVICE in livres utilisateurs emprunts recommandation frontend; do
                            docker tag bibliotheque-${SERVICE} $DOCKER_REGISTRY/bibliotheque/${SERVICE}:$IMAGE_TAG
                            docker tag bibliotheque-${SERVICE} $DOCKER_REGISTRY/bibliotheque/${SERVICE}:latest
                            docker push $DOCKER_REGISTRY/bibliotheque/${SERVICE}:$IMAGE_TAG
                            docker push $DOCKER_REGISTRY/bibliotheque/${SERVICE}:latest
                        done

                        docker logout $DOCKER_REGISTRY
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
            sh 'docker system prune -f || true'
            cleanWs()
        }
    }
}
