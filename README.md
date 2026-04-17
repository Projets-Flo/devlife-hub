# 🚀 DevLife Hub

> Tableau de bord personnel end-to-end construit pour m'aider au quotidien dans deux domaines :
> la **recherche d'emploi** (agrégation et triage d'offres) et le **suivi de mes performances sportives** (courses à pied et entraînements fractionné).
>
> Projet construit de A à Z — ingestion de données, stockage, visualisation, orchestration — avec une attention particulière portée aux bonnes pratiques (CI/CD, typage, tests, pre-commit).

---

## Contexte

Jeune diplômé ingénieur (Polytech Lyon — Mathématiques Appliquées & Modélisation, 2025), j'ai construit ce projet avec deux objectifs :

1. **Me rendre service au quotidien** — avoir un outil centralisé pour suivre mes offres d'emploi et mes entraînements
2. **Démontrer des compétences data end-to-end** — pipeline complet de la collecte à la visualisation, avec de vraies données

---

## Ce que fait le projet aujourd'hui

### 🔍 Module Job Search
- Connexion à l'**API officielle France Travail** (OAuth2) — collecte automatique des offres data science / ML / data analyst sur toute la France
- Déduplication automatique par `external_id` — pas de doublons entre les collectes
- Filtres par **région**, **département** (tous les 95 départements), zone prioritaire, ville libre
- Filtres par contrat, salaire, mots-clés
- **Système de triage** : chaque offre peut être marquée ✅ Intéressant / ⏳ À voir / ❌ Rejeté
- Vue **Favoris** : accès rapide aux offres sélectionnées
- Vue **Marché** : répartition des offres par région, types de contrats, fourchettes salariales
- Pipeline quotidien automatisable via **Prefect**

### 🏃 Module Sport

#### Courses endurance
- Import et parsing des exports **Samsung Health** (CSV) — format réel vérifié sur données personnelles
- Stockage persistant dans **PostgreSQL** — les données Samsung Health et les séances manuelles cohabitent en base
- Filtres : source native uniquement, durée minimum, exclusion des séances corrompues
- **Ajout manuel de séances** depuis le dashboard (formulaire complet : distance, durée, allure, FC, dénivelé, notes)
- **Modification et suppression** des séances manuelles depuis le dashboard
- Dashboard avec :
  - 8 métriques clés (km totaux, allure moyenne, meilleure sortie, FC moyenne, calories...)
  - Filtre de dates flexible (périodes prédéfinies ou plage personnalisée)
  - Graphe de progression des distances (scatter coloré par FC)
  - Évolution de l'allure dans le temps
  - Évolution de la fréquence cardiaque
  - Résumé par semaine / mois / année avec métriques de régularité
  - Tableau détaillé trié par n'importe quelle colonne
  - Durées et allures affichées en format lisible (5'16''/km, 50'12'', 1h03'24'')

#### Entraînements fractionné
- Saisie structurée par **blocs** dans l'ordre de la séance : échauffement, séries, récupération
- Trois types de blocs :
  - **Série simple** : N × distance avec temps individuels et récupération
  - **Série double** : N × (2 × distance) avec pause intra-groupe et récupération
  - **Échauffement / Récupération** : par distance ou par durée
- Tableau récapitulatif par distance : meilleur temps, meilleure vitesse, vitesse moyenne, dernière performance
- Graphe de progression de la **meilleure vitesse par séance** (ligne)
- Graphe de **toutes les répétitions** (scatter)
- Modification et suppression des séances depuis le dashboard

---

## Stack technique

### Actuellement en production

| Catégorie | Outils |
|-----------|--------|
| **Langages** | Python 3.11, SQL |
| **Dashboard** | Streamlit, Plotly |
| **Base de données** | PostgreSQL (Docker), SQLAlchemy 2.0 |
| **API backend** | FastAPI, Pydantic v2 |
| **Orchestration** | Prefect 3 |
| **Collecte** | France Travail API (OAuth2), httpx |
| **Data** | pandas, numpy, statsmodels |
| **Infra locale** | Docker, Docker Compose |
| **Qualité code** | Ruff, pre-commit, pytest |
| **CI/CD** | GitHub Actions |
| **Versioning** | Git, GitHub |

### Expérimental / prévu

| Outil | Usage | Statut |
|-------|-------|--------|
| **MLflow** | Tracking d'expériences ML | Configuré, pas encore utilisé en prod |
| **Prophet** | Prévision de charge d'entraînement | Prévu Phase 3 |
| **scikit-learn / XGBoost** | Modèles ML salary predictor | Prévu Phase 3 |

---

## Ce qui a été tenté et abandonné

### Analyse LLM des offres d'emploi (Ollama + Mistral 7B)

**Ce qu'on a construit** : un pipeline complet d'analyse sémantique des offres — Mistral 7B tournait en local via Ollama, analysait chaque offre et retournait un JSON structuré (score d'adéquation, compétences manquantes, salaire estimé, conseil de candidature, probabilité de succès...).

**Pourquoi ça a été abandonné** : le système fonctionnait techniquement, mais en pratique la valeur ajoutée était insuffisante. Mistral 7B hallucine des compétences, oublie des éléments du profil candidat, et au final lire l'offre directement est plus rapide et plus fiable que vérifier les analyses du modèle. Un LLM 7B local n'a pas la qualité suffisante pour ce cas d'usage précis.

**Ce que ça m'a appris** : l'importance de valider la valeur métier avant d'industrialiser un pipeline ML. Le système était propre techniquement (prompting structuré, retry logic, batch processing, sauvegarde incrémentale) mais la sortie n'était pas assez fiable pour être utile.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Sources                             │
│   France Travail API          Samsung Health CSV export  │
└──────────────┬────────────────────────┬─────────────────┘
               │                        │
               ▼                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Ingestion / Parsing                    │
│   job_collector.py (Prefect)   samsung_health.py parser  │
└──────────────┬────────────────────────┬─────────────────┘
               │                        │
               ▼                        ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL (Docker local)                   │
│   job_offers · workout_sessions · interval_sessions      │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI backend                        │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               Streamlit Dashboard                        │
│   Job Search · Triage · Favoris · Sport · Fractionné     │
└─────────────────────────────────────────────────────────┘
```

---

## Installation

### Prérequis
- Python 3.11+
- Docker & Docker Compose
- Git

### Setup

```bash
# Cloner le repo
git clone https://github.com/Projets-Flo/devlife-hub.git
cd devlife-hub

# Environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Dépendances
pip install -e ".[dev]"

# Pre-commit hooks
pre-commit install

# Variables d'environnement
cp .env.example .env
# Remplir .env avec les clés API (France Travail...)
```

### Lancer l'infrastructure

```bash
docker compose up -d db
```

### Lancer le dashboard

```bash
$env:PYTHONPATH="." ; streamlit run src/dashboard/app.py   # Windows
# PYTHONPATH=. streamlit run src/dashboard/app.py          # Linux/Mac
```

### Importer les données Samsung Health

1. Samsung Health → Profil → ⚙️ → Télécharger les données personnelles
2. Dézipper dans `data/exports/samsung_health/`
3. Importer en base PostgreSQL :

```bash
python -c "
from src.sport.parsers.samsung_health import SamsungHealthParser
from src.common.database import WorkoutSession, engine
from sqlalchemy.orm import Session

parser = SamsungHealthParser()
sessions = parser.parse_workouts()

with Session(engine) as session:
    existing = {o.external_id for o in session.query(WorkoutSession).all()}
    new = [s for s in sessions if s.external_id not in existing]
    for s in new:
        s.sport_type = s.sport_type.value
        session.add(s)
    session.commit()
    print(f'{len(new)} séances importées')
"
```

### Collecter les offres d'emploi

```bash
python -m src.jobs.scrapers.job_collector
```

---

## Structure du projet

```
devlife-hub/
├── .github/workflows/ci.yml         # CI/CD — lint + tests + Docker build
├── src/
│   ├── common/
│   │   ├── config.py                # Settings Pydantic (variables d'env)
│   │   ├── database.py              # Modèles SQLAlchemy
│   │   │                            #   JobOffer, WorkoutSession, IntervalSession
│   │   └── logger.py                # Loguru — format dev / prod
│   ├── jobs/
│   │   ├── scrapers/
│   │   │   ├── france_travail.py    # Client API France Travail (OAuth2)
│   │   │   └── job_collector.py     # Orchestrateur de collecte
│   │   ├── matching/
│   │   │   └── extractor.py         # Extraction règles-based (compétences)
│   │   └── flows/
│   │       └── daily_pipeline.py    # Pipeline Prefect quotidien
│   ├── sport/
│   │   └── parsers/
│   │       └── samsung_health.py    # Parser CSV Samsung Health
│   ├── api/
│   │   └── main.py                  # FastAPI — endpoints REST
│   └── dashboard/
│       ├── app.py                   # Streamlit — point d'entrée
│       └── modules/
│           └── jobs.py              # Page offres d'emploi (triage, filtres, stats)
├── tests/
│   └── unit/
│       └── test_samsung_parser.py
├── data/exports/samsung_health/     # Export Samsung (ignoré par git)
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## Évolutions prévues

### Module Sport
- [ ] Prévision de charge d'entraînement avec **Prophet** (time series)
- [ ] Plan d'entraînement adapté selon la météo (**OpenWeatherMap API**)
- [ ] Détection de surmenage / sous-entraînement

### Module Job Search
- [ ] Sources supplémentaires (Welcome to the Jungle)

### Infrastructure
- [ ] Déploiement cloud sur **Railway.app** (free tier)
- [ ] Stockage des données sur **Supabase** (PostgreSQL managed, gratuit)

---

## Auteur

**Florian Rey** — Ingénieur diplômé Polytech Lyon, Mathématiques Appliquées & Modélisation  
[LinkedIn](https://www.linkedin.com/in/florian-rey-910ab6262/) · [GitHub](https://github.com/Projets-Flo)