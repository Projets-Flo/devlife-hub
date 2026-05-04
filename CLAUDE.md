# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Lint & format
ruff check src/ tests/
ruff format src/ tests/
mypy src/

# Tests
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
pytest tests/unit/test_samsung_parser.py  # Run single test file

# Run locally (requires PostgreSQL or SQLite via DATABASE_URL)
PYTHONPATH=. streamlit run src/dashboard/app.py   # Dashboard on :8501
uvicorn src.api.main:app --reload                 # API on :8000

# Full stack with Docker
docker compose up                  # PostgreSQL + MLflow + Prefect + API + Dashboard
docker compose up -d db            # PostgreSQL only (minimal local dev)

# Prefect daily job collection
python -m src.jobs.flows.daily_pipeline
```

## Architecture

**DevLife Hub** is a personal dashboard tracking job search and fitness activities. Three layers:

1. **Streamlit Dashboard** (`src/dashboard/`) — primary UI, ~1800 lines in `app.py` with tab-based pages; `modules/jobs.py` handles the job search page
2. **FastAPI Backend** (`src/api/`) — thin REST API (`/health`, `/`, `PATCH /jobs/{id}/status`); CORS open to localhost:8501 and :3000
3. **PostgreSQL** — SQLAlchemy 2.0 declarative models in `src/common/database.py`; no Alembic migrations yet (tables created via `Base.metadata.create_all`)

### Data domains

**Jobs** (`src/jobs/`):
- `scrapers/france_travail.py` — OAuth2 client against France Travail API; token cached with 60s refresh buffer
- `scrapers/job_collector.py` — orchestrates searches across 16+ data science keywords
- `matching/extractor.py` — rule-based skill extraction from job descriptions
- `matching/llm_analyzer.py` — **abandoned** Mistral 7B attempt; hallucinations > value, left for reference
- `flows/daily_pipeline.py` — Prefect flow for scheduled daily collection

**Sport** (`src/sport/`):
- `parsers/samsung_health.py` — parses Samsung Health CSV exports; maps exercise type codes (1002 = running); has a hardcoded `EXCLUDED_DATES` list for corrupted sessions
- Dashboard tabs: Stats (8 KPIs with date filters), Detail (sortable table), Period (weekly/monthly/yearly aggregations), Add (manual entry + interval training), Manage (edit/delete)

### Database models (`src/common/database.py`)

| Model | Key columns |
|---|---|
| `JobOffer` | `status` enum (new/interesting/rejected/maybe), `tags` JSON, `match_score` float |
| `Application` | FK to JobOffer, `status`, `next_action_date` |
| `WorkoutSession` | `sport_type` enum, `source` (samsung/manual), `exercises` JSON |
| `IntervalSession` | `blocs` JSON — flexible structure with 4 bloc types |
| `TrainingPlan` | `plan_data` JSON, `weather_forecast` |
| `DailyAdvice` | `category` (job/sport/networking/skill), `done` bool — for future Claude coach |

### Configuration

All settings via `src/common/config.py` (Pydantic `BaseSettings`), loaded from `.env`. Key vars: `DATABASE_URL`, `ANTHROPIC_API_KEY`, France Travail OAuth credentials, `APP_ENV`. See `.env.example` for the full list.

Logging via Loguru (`src/common/logger.py`): colorized in dev, structured JSON in prod. No `print()` statements — use `logger`.

### Code conventions

- **Session pattern**: `with Session(engine) as session:` everywhere
- **Streamlit caching**: `@st.cache_data(ttl=60)` on DB-reading functions; call `st.cache_data.clear()` after mutations
- **Form keys**: prefixed with context (e.g., `serie_rep_{i}`, `edit_int_date_{session_id}`) to avoid Streamlit key collisions
- **Pace display**: decimal input `5.27` means 5 min 27 sec/km; utility functions convert to/from `5'27''/km`
- **Track time**: stored as centiseconds; formatted as `MM'SS''CS`
- **JSON columns**: used for flexible schemas (`tags`, `exercises`, `blocs`) — avoid schema migrations for evolving structures
- **Ruff config**: line-length=100, rules E, F, I, UP, B; target py311

### Planned but not yet implemented

- Claude API coach module (`src/coach/`) — `ANTHROPIC_API_KEY` is wired in config, `DailyAdvice` table exists
- ML models (`src/ml/`) — MLflow + DVC infrastructure ready, no trained models
- Alembic migrations — not initialized; schema changes require manual `CREATE/ALTER TABLE` or dropping and recreating
- Weather integration (`src/sport/weather/`) — stubbed only
