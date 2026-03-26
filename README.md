# 🚀 DevLife Hub

> Dashboard personnel end-to-end : recherche d'emploi intelligente, suivi sportif & coaching quotidien.
> **Stack** : Python · FastAPI · Streamlit · PostgreSQL · MLflow · DVC · Docker · AWS

---

## Architecture

```
Sources (Job boards FR/CH, Samsung Health, OpenWeather, CV)
    ↓ Prefect DAGs (scraping & ingestion)
Storage (PostgreSQL + AWS S3 + DVC)
    ↓
ML Pipeline (NLP matching, XGBoost salary, Prophet forecasting)
    ↓ FastAPI
Frontends : Streamlit dashboard · Telegram Bot · Portfolio public
```

## Modules

| Module | Description | Stack clé |
|--------|-------------|-----------|
| 🔍 **Job Search** | Scraping multi-sources FR+CH, matching NLP CV↔offres, suivi candidatures | Playwright, sentence-transformers, XGBoost |
| 🏃 **Sport** | Import Samsung Health, plan adapté météo, forecasting charge | Prophet, OpenWeatherMap |
| 🎯 **Coach** | Conseils quotidiens, simulateur d'entretien, gap analyzer | Claude API |
| ⚙️ **ML** | Pipeline MLOps complet, model registry, CI/CD | MLflow, DVC, GitHub Actions |

---

## Démarrage rapide

### 1. Prérequis

- Python 3.11+
- Docker & Docker Compose
- Git

### 2. Installation

```bash
# Cloner le repo
git clone https://github.com/ton-username/devlife-hub.git
cd devlife-hub

# Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

# Installer les dépendances
pip install -e ".[dev]"

# Installer les hooks pre-commit
pre-commit install

# Copier et configurer les variables d'environnement
cp .env.example .env
# Édite .env avec tes clés API
```

### 3. Lancer l'infrastructure locale

```bash
# Démarre PostgreSQL + MLflow + Prefect + API + Dashboard
docker compose up -d

# Vérifier que tout est up
docker compose ps
```

### 4. Accès aux services

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:8501 | Streamlit UI |
| API | http://localhost:8000/docs | FastAPI Swagger |
| MLflow | http://localhost:5000 | Tracking expériences |
| Prefect | http://localhost:4200 | Orchestration DAGs |

### 5. Import Samsung Health

1. Samsung Health app → Profil → Paramètres → **Télécharger mes données**
2. Place le ZIP dans `data/exports/samsung_health/`
3. Lance le parser :

```bash
python -c "
from src.sport.parsers.samsung_health import SamsungHealthParser
parser = SamsungHealthParser()
sessions = parser.parse_workouts()
df = parser.to_dataframe(sessions)
print(df.head())
"
```

---

## Structure du projet

```
devlife-hub/
├── .github/workflows/      # CI/CD GitHub Actions
├── data/
│   ├── raw/                # Données brutes (ignorées par git, versionnées DVC)
│   ├── processed/          # Données transformées
│   └── exports/samsung_health/
├── src/
│   ├── common/             # Config, BDD, logger
│   ├── jobs/               # Module Job Search
│   │   ├── scrapers/       # Playwright scrapers
│   │   └── matching/       # NLP matcher
│   ├── sport/              # Module Sport
│   │   ├── parsers/        # Samsung Health parser
│   │   └── planner/        # Générateur de plans
│   ├── coach/              # Module Coach (Claude API)
│   ├── ml/                 # Pipelines ML
│   │   ├── salary/         # Prédiction salariale
│   │   ├── matching/       # Job matching NLP
│   │   └── forecasting/    # Charge d'entraînement
│   ├── api/                # FastAPI
│   └── dashboard/          # Streamlit
├── tests/
├── notebooks/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## Roadmap

- [ ] **Phase 0** — Setup & fondations (actuellement ici)
- [ ] **Phase 1** — MVP Dashboard (Streamlit + scraping manuel)
- [ ] **Phase 2** — Automatisation (Prefect DAGs, alertes Telegram)
- [ ] **Phase 3** — Couche ML (NLP, XGBoost, Prophet, MLflow)
- [ ] **Phase 4** — MLOps & déploiement cloud (Docker + AWS)

---

## Pour les entretiens

Ce projet démontre :
- **Pipeline end-to-end** : ingestion → transformation → ML → déploiement
- **MLOps** : MLflow (experiment tracking), DVC (data versioning), CI/CD
- **NLP** : sentence-transformers pour le matching sémantique CV/offres
- **Time series** : Prophet pour la prédiction de charge d'entraînement
- **Cloud** : AWS S3 (storage), Lambda/Cloud Run (déploiement)
- **Bonnes pratiques** : tests, type hints, pre-commit, Docker, GitHub Actions
