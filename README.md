# 🚀 DevLife Hub

> Tableau de bord personnel end-to-end construit pour m'aider au quotidien dans deux domaines :
> la **recherche d'emploi** (agrégation et triage d'offres) et le **suivi de mes performances sportives** (courses à pied).
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
- Import et parsing des exports **Samsung Health** (CSV) — format réel vérifié sur données personnelles
- 72 courses à pied validées — correspondance exacte avec les totaux Samsung Health
- Filtres : source native uniquement, durée minimum, exclusion des séances corrompues
- Dashboard **Streamlit** avec :
  - 8 métriques clés (km totaux, allure moyenne, meilleure sortie, FC moyenne, calories...)
  - Graphe de progression des distances (scatter coloré par FC)
  - Évolution de l'allure dans le temps
  - Évolution de la fréquence cardiaque
  - Résumé par semaine / mois / année (toggle interactif)
  - Tableau détaillé de toutes les séances

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
| **Data** | pandas, numpy |
| **Infra locale** | Docker, Docker Compose |
| **Qualité code** | Ruff, pre-commit, pytest |
| **CI/CD** | GitHub Actions |
| **Versioning** | Git, GitHub |

### Expérimental / utilisé en développement

| Outil | Usage | Statut |
|-------|-------|--------|
| **MLflow** | Tracking d'expériences ML | Configuré, pas encore utilisé en prod |
| **Ollama / Mistral 7B** | Analyse LLM locale des offres | Abandonné (voir section ci-dessous) |

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
│         job_offers · applications · workout_sessions     │
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
│   Job Search · Triage · Favoris · Sport · Marché         │
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
git clone https://github.com/Flomfoot/devlife-hub.git
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
# Remplir .env avec les clés API (France Travail, OpenWeather...)
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

### Collecter les offres d'emploi

```bash
python -m src.jobs.scrapers.job_collector
```

### Importer les données Samsung Health

1. Samsung Health → Profil → ⚙️ → Télécharger les données personnelles
2. Dézipper dans `data/exports/samsung_health/`
3. Relancer le dashboard — les données sont chargées automatiquement

---

## Structure du projet

```
devlife-hub/
├── .github/workflows/ci.yml        # CI/CD — lint + tests + Docker build
├── src/
│   ├── common/
│   │   ├── config.py               # Settings Pydantic (variables d'env)
│   │   ├── database.py             # Modèles SQLAlchemy (JobOffer, WorkoutSession...)
│   │   └── logger.py               # Loguru — format dev / prod
│   ├── jobs/
│   │   ├── scrapers/
│   │   │   ├── france_travail.py   # Client API France Travail (OAuth2)
│   │   │   └── job_collector.py    # Orchestrateur de collecte
│   │   ├── matching/
│   │   │   └── extractor.py        # Extraction règles-based (compétences, expérience)
│   │   └── flows/
│   │       └── daily_pipeline.py   # Pipeline Prefect quotidien
│   ├── sport/
│   │   └── parsers/
│   │       └── samsung_health.py   # Parser CSV Samsung Health
│   ├── api/
│   │   └── main.py                 # FastAPI — endpoints REST
│   └── dashboard/
│       ├── app.py                  # Streamlit — point d'entrée
│       └── modules/
│           └── jobs.py             # Page offres d'emploi (triage, filtres, stats)
├── tests/
│   └── unit/
│       └── test_samsung_parser.py
├── data/exports/samsung_health/    # Export Samsung (ignoré par git)
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## Évolutions prévues

### Module Sport
- [ ] Saisie manuelle d'une séance directement depuis le dashboard (formulaire)
- [ ] Prédiction de charge d'entraînement avec **Prophet** (time series)
- [ ] Plan d'entraînement généré automatiquement selon la météo (**OpenWeatherMap API**)
- [ ] Détection de surmenage / sous-entraînement

### Infrastructure
- [ ] Déploiement cloud sur **Railway.app** ou **GCP Cloud Run** (free tier)
- [ ] Stockage des données sur **Supabase** (PostgreSQL managed, gratuit)

---

## Auteur

**Florian Rey** — Ingénieur diplômé Polytech Lyon, Mathématiques Appliquées & Modélisation
[LinkedIn](https://www.linkedin.com/in/florian-rey-910ab6262/) · [GitHub](https://github.com/Projets-Flo)
