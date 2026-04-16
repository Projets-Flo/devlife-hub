"""
Base de données — SQLAlchemy 2.0 avec tous les modèles du projet.
Migrations gérées par Alembic.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from src.common.config import settings

# ── Base & engine ─────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.is_development,
)


def get_session() -> Session:
    """Dependency FastAPI / usage direct."""
    with Session(engine) as session:
        yield session


def create_all_tables() -> None:
    Base.metadata.create_all(engine)


# ── Enums ─────────────────────────────────────────────────────────────────────


class JobStatus(PyEnum):
    NEW = "new"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


class ContractType(PyEnum):
    CDI = "CDI"
    CDD = "CDD"
    INTERNSHIP = "stage"
    FREELANCE = "freelance"
    APPRENTICESHIP = "alternance"


class SportType(PyEnum):
    RUNNING = "running"
    WALKING = "walking"
    CYCLING = "cycling"
    STRENGTH = "strength"
    OTHER = "other"

    def __str__(self):
        return self.value


# ── Modèles Job Search ────────────────────────────────────────────────────────


class JobOffer(Base):
    """Offre d'emploi agrégée depuis les différentes sources."""

    __tablename__ = "job_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50))  # linkedin, indeed, jobs_ch, etc.
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    contract_type: Mapped[str | None] = mapped_column(String(50))
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(10))
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[dict | None] = mapped_column(JSON)  # skills, technologies
    match_score: Mapped[float | None] = mapped_column(Float)  # NLP cosine similarity
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=True)
    # new | interesting | rejected | maybe
    predicted_salary: Mapped[float | None] = mapped_column(Float)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    applications: Mapped[list["Application"]] = relationship(back_populates="offer")


class Application(Base):
    """Suivi des candidatures."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("job_offers.id"))
    status: Mapped[str] = mapped_column(String(50), default=JobStatus.APPLIED)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(String(300))
    next_action_date: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    offer: Mapped["JobOffer"] = relationship(back_populates="applications")


# ── Modèles Sport ─────────────────────────────────────────────────────────────


class WorkoutSession(Base):
    """Séance d'entraînement (import Samsung Health ou saisie manuelle)."""

    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    sport_type: Mapped[str] = mapped_column(String(50))
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_minutes: Mapped[float | None] = mapped_column(Float)
    distance_km: Mapped[float | None] = mapped_column(Float)
    calories: Mapped[int | None] = mapped_column(Integer)
    avg_heart_rate: Mapped[int | None] = mapped_column(Integer)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer)
    avg_pace_min_km: Mapped[float | None] = mapped_column(Float)  # running
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    # Musculation spécifique
    exercises: Mapped[dict | None] = mapped_column(JSON)
    # Métadonnées météo au moment de la séance
    weather_temp_c: Mapped[float | None] = mapped_column(Float)
    weather_condition: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(50), default="manual")  # samsung, manual
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TrainingPlan(Base):
    """Plan d'entraînement généré pour la semaine."""

    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[datetime] = mapped_column(DateTime)
    plan_data: Mapped[dict] = mapped_column(JSON)  # {lundi: {...}, mardi: {...}, ...}
    weather_forecast: Mapped[dict | None] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ── Modèles Coach & CV ───────────────────────────────────────────────────────


class CVProfile(Base):
    """Profil extrait du CV, mis à jour manuellement ou via parsing."""

    __tablename__ = "cv_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skills: Mapped[dict | None] = mapped_column(JSON)  # {hard: [], soft: []}
    experiences: Mapped[dict | None] = mapped_column(JSON)
    education: Mapped[dict | None] = mapped_column(JSON)
    languages: Mapped[dict | None] = mapped_column(JSON)
    embedding: Mapped[list | None] = mapped_column(JSON)  # vecteur NLP du CV
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class DailyAdvice(Base):
    """Conseil quotidien généré par Claude API."""

    __tablename__ = "daily_advices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    category: Mapped[str] = mapped_column(String(50))  # job, sport, networking, skill
    content: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1=urgent 2=normal 3=nice
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
