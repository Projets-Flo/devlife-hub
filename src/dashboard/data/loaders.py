import pandas as pd
import streamlit as st

from src.sport.parsers.samsung_health import SamsungHealthParser


@st.cache_data(ttl=60, show_spinner="Chargement des courses…")
def load_runs():
    from sqlalchemy.orm import Session as DBSession

    from src.common.database import WorkoutSession, engine

    with DBSession(engine) as session:
        all_sessions = session.query(WorkoutSession).order_by(WorkoutSession.date).all()
        session.expunge_all()

    rows = []
    for s in all_sessions:
        if str(s.sport_type).lower() not in ["sporttype.running", "running"]:
            continue
        if not s.distance_km or s.distance_km < 1:
            continue
        if not s.duration_minutes or s.duration_minutes < 2:
            continue
        rows.append(
            {
                "id": s.id,
                "date": s.date,
                "sport_type": "running",
                "distance_km": s.distance_km,
                "duration_min": s.duration_minutes,
                "avg_hr": s.avg_heart_rate,
                "max_hr": s.max_heart_rate,
                "avg_pace_min_km": s.avg_pace_min_km,
                "elevation_m": s.elevation_gain_m,
                "calories": s.calories,
                "source": s.source or "manual",
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df, SamsungHealthParser()


@st.cache_data(ttl=60, show_spinner="Chargement des fractionnés…")
def load_intervals():
    from sqlalchemy.orm import Session as DBSession

    from src.common.database import IntervalSession, engine

    with DBSession(engine) as session:
        sessions = session.query(IntervalSession).order_by(IntervalSession.date.desc()).all()
        session.expunge_all()
    return sessions
