"""
Parser Samsung Health — format réel de l'export (vérifié sur mes données).

Structure de l'export :
  samsunghealth/
  ├── com.samsung.shealth.exercise.YYYYMMDDHHMMSS.csv  ← résumé de toutes les séances
  └── jsons/com.samsung.shealth.exercise/              ← données détaillées (FC/s, GPS)

Usage :
    from src.sport.parsers.samsung_health import SamsungHealthParser
    parser = SamsungHealthParser()
    sessions = parser.parse_workouts()
    df = parser.to_dataframe(sessions)
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from src.common.config import settings
from src.common.database import SportType, WorkoutSession

ACTIVITY_MAP: dict[int, str] = {
    1002: SportType.RUNNING,
}

COL = {
    "uuid": "com.samsung.health.exercise.datauuid",
    "start": "com.samsung.health.exercise.start_time",
    "end": "com.samsung.health.exercise.end_time",
    "duration": "com.samsung.health.exercise.duration",
    "type": "com.samsung.health.exercise.exercise_type",
    "distance": "com.samsung.health.exercise.distance",
    "calorie": "com.samsung.health.exercise.calorie",
    "hr_mean": "com.samsung.health.exercise.mean_heart_rate",
    "hr_max": "com.samsung.health.exercise.max_heart_rate",
    "hr_min": "com.samsung.health.exercise.min_heart_rate",
    "speed_mean": "com.samsung.health.exercise.mean_speed",
    "speed_max": "com.samsung.health.exercise.max_speed",
    "alt_gain": "com.samsung.health.exercise.altitude_gain",
    "alt_loss": "com.samsung.health.exercise.altitude_loss",
}

EXCLUDE_KEYWORDS = [
    "hr_zone",
    "max_heart_rate",
    "weather",
    "extension",
    "recovery",
    "periodization",
]


class SamsungHealthParser:
    """Parse les exports Samsung Health en objets WorkoutSession."""

    def __init__(self, export_dir: Path | str | None = None):
        self.export_dir = Path(export_dir or settings.samsung_health_export_dir)
        self.data_dir = self._find_data_dir()

    def _find_data_dir(self) -> Path:
        if list(self.export_dir.glob("com.samsung.shealth.exercise.*.csv")):
            return self.export_dir
        sub = self.export_dir / "samsunghealth"
        if sub.exists():
            return sub
        return self.export_dir

    def parse_workouts(self) -> list[WorkoutSession]:
        csv_files = sorted(self.data_dir.glob("com.samsung.shealth.exercise.*.csv"))
        csv_files = [f for f in csv_files if not any(kw in f.name for kw in EXCLUDE_KEYWORDS)]

        if not csv_files:
            logger.warning(f"Aucun fichier exercise trouvé dans {self.data_dir}.")
            return []

        all_sessions: list[WorkoutSession] = []
        for f in csv_files:
            logger.info(f"Parsing : {f.name}")
            all_sessions.extend(self._parse_csv(f))

        logger.success(f"{len(all_sessions)} séances importées depuis Samsung Health")
        return all_sessions

    def _parse_csv(self, csv_path: Path) -> list[WorkoutSession]:
        try:
            df = pd.read_csv(
                csv_path, skiprows=1, low_memory=False, on_bad_lines="skip", index_col=False
            )
        except Exception as e:
            logger.error(f"Impossible de lire {csv_path.name} : {e}")
            return []

        sessions = []
        for _, row in df.iterrows():
            s = self._row_to_session(row)
            if s:
                sessions.append(s)
        return sessions

    def _row_to_session(self, row: pd.Series) -> WorkoutSession | None:
        try:
            raw_type = row.get(COL["type"])
            if pd.isna(raw_type):
                return None
            sport_type = ACTIVITY_MAP.get(int(float(raw_type)), SportType.OTHER)

            pkg = row.get("com.samsung.health.exercise.pkg_name")
            if pkg != "com.sec.android.app.shealth":
                return None

            raw_start = row.get(COL["start"])
            if pd.isna(raw_start):
                return None
            start_dt = pd.to_datetime(raw_start, utc=False).to_pydatetime()

            raw_dur = row.get(COL["duration"])
            duration_min = round(float(raw_dur) / 60000, 1) if pd.notna(raw_dur) else None

            raw_dist = row.get(COL["distance"])
            distance_km = round(float(raw_dist) / 1000, 3) if pd.notna(raw_dist) else None

            raw_cal = row.get(COL["calorie"])
            calories = int(float(raw_cal)) if pd.notna(raw_cal) else None

            raw_hr = row.get(COL["hr_mean"])
            hr_mean = int(float(raw_hr)) if pd.notna(raw_hr) else None

            raw_hrmax = row.get(COL["hr_max"])
            hr_max = int(float(raw_hrmax)) if pd.notna(raw_hrmax) else None

            avg_pace = None
            raw_speed = row.get(COL["speed_mean"])
            if pd.notna(raw_speed) and float(raw_speed) > 0:
                avg_pace = round(1000 / (float(raw_speed) * 60), 2)

            raw_gain = row.get(COL["alt_gain"])
            elevation = round(float(raw_gain), 1) if pd.notna(raw_gain) else None

            raw_uuid = row.get(COL["uuid"])
            external_id = str(raw_uuid) if pd.notna(raw_uuid) else None

            return WorkoutSession(
                external_id=external_id,
                sport_type=sport_type,
                date=start_dt,
                duration_minutes=duration_min,
                distance_km=distance_km,
                calories=calories,
                avg_heart_rate=hr_mean,
                max_heart_rate=hr_max,
                avg_pace_min_km=avg_pace,
                elevation_gain_m=elevation,
                source="samsung",
            )
        except Exception as e:
            logger.warning(f"Ligne ignorée ({e})")
            return None

    def to_dataframe(self, sessions: list[WorkoutSession]) -> pd.DataFrame:
        if not sessions:
            return pd.DataFrame()
        rows = [
            {
                "date": s.date,
                "sport_type": s.sport_type,
                "duration_min": s.duration_minutes,
                "distance_km": s.distance_km,
                "calories": s.calories,
                "avg_hr": s.avg_heart_rate,
                "max_hr": s.max_heart_rate,
                "avg_pace_min_km": s.avg_pace_min_km,
                "elevation_m": s.elevation_gain_m,
            }
            for s in sessions
        ]
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)

    def stats_running(self, df: pd.DataFrame) -> dict:
        runs = df.copy()
        if runs.empty:
            return {}
        return {
            "total_sessions": len(runs),
            "total_km": round(runs["distance_km"].sum(), 1),
            "avg_km": round(runs["distance_km"].mean(), 1),
            "best_km": round(runs["distance_km"].max(), 1),
            "avg_pace": round(runs["avg_pace_min_km"].mean(), 2),
            "best_pace": round(runs["avg_pace_min_km"].min(), 2),
            "avg_hr": round(runs["avg_hr"].mean(), 0),
            "total_calories": int(runs["calories"].sum()),
        }

    def weekly_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["week"] = df["date"].dt.to_period("W")
        return (
            df.groupby(["week", "sport_type"])
            .agg(
                sessions=("date", "count"),
                total_km=("distance_km", "sum"),
                total_min=("duration_min", "sum"),
                avg_hr=("avg_hr", "mean"),
            )
            .round(1)
            .reset_index()
        )
