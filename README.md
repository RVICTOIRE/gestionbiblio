# Bibliothèque Numérique DIT — Système de Recommandation

> Projet d'examen — Master 2 Intelligence Artificielle  
> Outils de Versioning — Dakar Institute of Technology  
> Du 24 Avril 2026 au 15 Mai 2026

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (Nginx:80)                  │
│              HTML / CSS / JavaScript                     │
└───────────┬────────────┬──────────────┬─────────────────┘
            │            │              │
    /api/books   /api/users   /api/loans    /api/recommendations
            │            │              │              │
    ┌───────▼──┐  ┌──────▼──┐  ┌───────▼──┐  ┌───────▼──────┐
    │  LIVRES  │  │  USERS  │  │ EMPRUNTS │  │ RECOMMANDATION│
    │ Flask    │  │  Flask  │  │  Flask   │  │   FastAPI     │
    │ :5001    │  │  :5002  │  │  :5003   │  │    :8000      │
    └────┬─────┘  └────┬────┘  └────┬─────┘  └───────┬──────┘
         │             │            │                 │
    ┌────▼─────────────▼────────────▼─────────────────▼──────┐
    │                  PostgreSQL :5432                        │
    │               Base de données partagée                  │
    └─────────────────────────────────────────────────────────┘
```

## Services

| Service          | Technologie     | Port | Description                          |
|------------------|-----------------|------|--------------------------------------|
| `livres`         | Flask + Psycopg2| 5001 | CRUD livres + recherche              |
| `utilisateurs`   | Flask + Psycopg2| 5002 | CRUD utilisateurs + types            |
| `emprunts`       | Flask + Psycopg2| 5003 | Emprunts + historique + export CSV   |
| `recommandation` | FastAPI + SKlearn| 8000| KNN collaboratif + ré-entraînement   |
| `frontend`       | Nginx + HTML/JS | 80   | Interface utilisateur                |
| `db`             | PostgreSQL 16   | 5432 | Base de données relationnelle        |

---

## Installation et lancement avec Docker Compose

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) ≥ 24.0
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.20

### Lancement en mode production

```bash
# Cloner le dépôt
git clone https://github.com/<votre-compte>/bibliotheque-dit.git
cd bibliotheque-dit

# Construire et démarrer tous les services
docker compose --profile prod up -d --build

# Vérifier que tout est opérationnel
docker compose ps
```

L'application est accessible sur **http://localhost**

### Lancement en mode développement (hot-reload)

```bash
# Mode dev : volumes montés, rechargement automatique
docker compose --profile dev up

# Avec reconstruction forcée
docker compose --profile dev up --build
```

### Arrêter les services

```bash
docker compose down          # Arrêt sans suppression des volumes
docker compose down -v       # Arrêt + suppression des volumes
```

---

## Initialisation de la base de données

La base de données est **automatiquement initialisée** au premier démarrage grâce au fichier `init.sql` monté dans le conteneur PostgreSQL.

Ce fichier crée :
- Les tables `books`, `users`, `loans`
- 12 livres de test (informatique, IA, data science…)
- 10 utilisateurs (étudiants, professeurs, personnel)
- 25 emprunts historiques pour l'entraînement ML

Pour réinitialiser manuellement :

```bash
docker compose exec db psql -U postgres -d bibliotheque -f /docker-entrypoint-initdb.d/init.sql
```

---

## APIs — Tests des endpoints

### Service Livres (port 5001)

```bash
# Lister tous les livres
curl http://localhost:5001/books

# Chercher un livre
curl "http://localhost:5001/books/search?q=python&type=title"

# Ajouter un livre
curl -X POST http://localhost:5001/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Clean Architecture","author":"Robert Martin","isbn":"978-0134494166","genre":"Génie Logiciel","total_copies":2}'

# Modifier un livre
curl -X PUT http://localhost:5001/books/1 \
  -H "Content-Type: application/json" \
  -d '{"available_copies": 3}'

# Supprimer un livre
curl -X DELETE http://localhost:5001/books/1
```

### Service Utilisateurs (port 5002)

```bash
# Lister tous les utilisateurs
curl http://localhost:5002/users

# Filtrer par type
curl "http://localhost:5002/users?type=etudiant"

# Créer un utilisateur
curl -X POST http://localhost:5002/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Moussa Diallo","email":"m.diallo@dit.sn","user_type":"etudiant","student_id":"DIT2024010"}'

# Profil complet
curl http://localhost:5002/users/1/profile
```

### Service Emprunts (port 5003)

```bash
# Lister les emprunts actifs
curl "http://localhost:5003/loans?status=actif"

# Emprunter un livre
curl -X POST http://localhost:5003/loans \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "book_id": 2}'

# Retourner un livre
curl -X PUT http://localhost:5003/loans/1/return

# Voir les emprunts en retard
curl http://localhost:5003/loans/overdue

# Historique d'un utilisateur
curl http://localhost:5003/loans/user/1

# Export CSV pour ML
curl http://localhost:5003/loans/export -o loans.csv
```

### Service Recommandation (port 8000)

```bash
# Recommandations pour l'utilisateur 1
curl http://localhost:8000/recommendations/1

# Recommandations avec plus de résultats
curl "http://localhost:8000/recommendations/1?n=10"

# Ré-entraîner le modèle
curl -X POST http://localhost:8000/train

# Informations sur le modèle
curl http://localhost:8000/model/info

# Documentation Swagger auto-générée
open http://localhost:8000/docs
```

---

## Pipeline DVC — Entraînement et reproduction du modèle

### Installation de DVC

```bash
pip install dvc dvc-gdrive
```

### Configuration du remote Google Drive

```bash
# Initialiser DVC (si pas déjà fait)
dvc init

# Configurer le remote Google Drive
dvc remote add -d gdrive gdrive://<FOLDER_ID>
dvc remote modify gdrive gdrive_acknowledge_abuse true

# Authentification
dvc push  # Se connecte à Google Drive
```

### Exécuter le pipeline complet

```bash
# Télécharger les données et le modèle depuis le remote
dvc pull

# Reproduire le pipeline (seulement les étapes modifiées)
dvc repro

# Forcer la réexécution complète
dvc repro --force
```

### Étapes du pipeline (`dvc.yaml`)

```
data/loans.csv
      │
      ▼ preprocess.py
data/loans_clean.csv
      │
      ▼ train.py
model/model.pkl
      │
      ▼ evaluate.py
metrics.json
```

1. **preprocess** — Nettoyage des données, calcul des scores implicites
2. **train** — Entraînement KNN (n_neighbors=10, metric=cosine)
3. **evaluate** — Calcul RMSE, MAE, coverage

### Afficher les métriques

```bash
# Afficher les métriques actuelles
dvc metrics show

# Comparer deux versions du modèle
dvc metrics diff v1.0.0 v1.1.0

# Exemple de sortie :
# Path          Metric   v1.0.0   v1.1.0   Change
# metrics.json  rmse     0.2341   0.1987   -0.0354
# metrics.json  mae      0.1876   0.1543   -0.0333
```

### Versionner le modèle

```bash
# Après entraînement, pusher le modèle
dvc push

# Commiter le dvc.lock (hash du modèle)
git add dvc.lock metrics.json
git commit -m "chore: modele v1.1.0 avec n_neighbors=10"
git tag -a v1.1.0 -m "Modele v1.1.0"

# Charger une version précédente
git checkout v1.0.0
dvc checkout  # Restaure model/model.pkl correspondant
```

---

## Workflow Git

```
master
  │
  ├── feature/services-base       ← Services Livres, Utilisateurs, Emprunts
  ├── feature/recommendation-service ← FastAPI + KNN
  ├── feature/frontend            ← Interface HTML/JS
  ├── feature/docker              ← Docker Compose
  ├── feature/dvc-pipeline        ← Scripts ML + dvc.yaml
  └── feature/model-v2            ← Expérimentation modèle
```

Consulter l'historique :

```bash
git log --oneline --graph --all
git log --oneline --decorate --graph
```

---

## CI/CD avec Jenkins (Bonus)

Le `Jenkinsfile` définit un pipeline avec les étapes :

1. **Checkout** — Récupération du code
2. **Lint & Validation** — Python flake8, Docker Compose config, DVC
3. **Build** — Construction des images Docker
4. **Tests** — Tests de santé des services
5. **DVC Pipeline** — `dvc repro` + push des artefacts
6. **Push Registry** — Images taguées vers le registry (sur `master`)
7. **Deploy Production** — `docker compose --profile prod up -d`

---

## Structure du projet

```
Examen_outil_versionning/
├── services/
│   ├── livres/            # Service Livres (Flask)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── utilisateurs/      # Service Utilisateurs (Flask)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── emprunts/          # Service Emprunts (Flask)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── recommandation/    # Service Recommandation (FastAPI)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile     ← Multi-stage build
│   └── frontend/          # Frontend (Nginx + HTML/JS)
│       ├── index.html
│       ├── nginx.conf
│       ├── Dockerfile
│       └── static/
│           ├── css/style.css
│           └── js/app.js
├── ml/
│   ├── preprocess.py      # Nettoyage des données
│   ├── train.py           # Entraînement KNN
│   └── evaluate.py        # RMSE, MAE, coverage
├── data/
│   ├── loans.csv          # Données brutes (géré par DVC)
│   └── loans.csv.dvc      # Pointeur DVC
├── model/
│   └── model.pkl          # Modèle entraîné (géré par DVC)
├── init.sql               # Schéma + données de test PostgreSQL
├── docker-compose.yml     # Orchestration complète
├── dvc.yaml               # Définition du pipeline DVC
├── dvc.lock               # Hash des artefacts (reproductibilité)
├── params.yaml            # Hyperparamètres du modèle
├── metrics.json           # Résultats v1.0.0
├── metrics_v2.json        # Résultats v1.1.0
├── Jenkinsfile            # Pipeline CI/CD
├── .gitignore
└── README.md
```

---

## Barème couvert

| Partie | Points | Statut |
|--------|--------|--------|
| Développement application (services + reco + frontend) | 6 | ✅ |
| Git Avancé (branches, merges, tags) | 4 | ✅ |
| Docker & Docker Compose (Dockerfiles + profils) | 4 | ✅ |
| DVC (pipeline, métriques, versioning modèle) | 6 | ✅ |
| **Total** | **20** | |
| Bonus CI/CD Jenkins | +2 | ✅ |
