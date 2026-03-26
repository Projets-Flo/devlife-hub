"""
Parser Samsung Health — importe tes données de course et d'activité.

Samsung Health exporte un ZIP contenant plusieurs CSV/JSON selon le type de donnée.
Dézippe l'export dans : data/exports/samsung_health/

Fichiers clés dans le ZIP :
  - com.samsung.shealth.exercise.*.csv           → séances (running, musculation…)
  - com.samsung.shealth.tracker.heart_rate.*.csv → fréquence cardiaque
  - com.samsung.shealth.sleep.stage.*.csv        → sommeil
  - com.samsung.shealth.step_daily_trend.*.csv   → pas quotidiens

Usage :
    from src.sport.parsers.samsung_health import SamsungHealthParser
    parser = SamsungHealthParser("data/exports/samsung_health")
    sessions = parser.parse_workouts()
    df = parser.to_dataframe(sessions)
"""

import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from loguru import logger

from src.common.config import settings
from src.common.database import SportType, WorkoutSession

# Mapping des types d'activité Samsung → enum interne
ACTIVITY_MAP: dict[int, str] = {
    1001: SportType.RUNNING,
    1002: SportType.WALKING,
    3001: SportType.CYCLING,
    10001: SportType.STRENGTH,
    # Compléter avec les codes de ta montre si besoin
    # Samsung health activity type codes : https://developer.samsung.com/health/android/data/api-reference/constant-values.html
}


class SamsungHealthParser:
    """Parse les exports Samsung Health en objets WorkoutSession."""

    def __init__(self, export_dir: Path | str | None = None):
        self.export_dir = Path(export_dir or settings.samsung_health_export_dir)

    # ── Entrée principale ─────────────────────────────────────────────────────

    def parse_workouts(self) -> list[WorkoutSession]:
        """
        Cherche tous les fichiers exercise dans export_dir et les convertit.
        Accepte aussi les ZIP directement.
        """
        sessions: list[WorkoutSession] = []
        csv_files = list(self.export_dir.glob("com.samsung.shealth.exercise.*.csv"))

        if not csv_files:
            logger.warning(
                f"Aucun fichier exercise trouvé dans {self.export_dir}. "
                "Dézippe ton export Samsung Health dans ce dossier."
            )
            return sessions

        for f in csv_files:
            logger.info(f"Parsing : {f.name}")
            sessions.extend(self._parse_exercise_csv(f))

        logger.success(f"{len(sessions)} séances importées depuis Samsung Health")
        return sessions

    def extract_zip(self, zip_path: Path) -> None:
        """Extrait un export ZIP Samsung Health dans export_dir."""
        self.export_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(self.export_dir)
        logger.success(f"ZIP extrait dans {self.export_dir}")

    # ── Parsing interne ───────────────────────────────────────────────────────

    def _parse_exercise_csv(self, csv_path: Path) -> list[WorkoutSession]:
        """
        Parse un fichier com.samsung.shealth.exercise.*.csv
        Les premières lignes peuvent contenir des métadonnées Samsung — on les saute.
        """
        sessions: list[WorkoutSession] = []

        # Samsung Health met parfois un header propriétaire sur les 2 premières lignes
        try:
            df = pd.read_csv(csv_path, comment="#", low_memory=False)
        except Exception:
            df = pd.read_csv(csv_path, skiprows=2, low_memory=False)

        logger.debug(f"Colonnes disponibles : {list(df.columns)}")

        for _, row in df.iterrows():
            session = self._row_to_session(row)
            if session:
                sessions.append(session)

        return sessions

    def _row_to_session(self, row: pd.Series) -> WorkoutSession | None:
        """Convertit une ligne CSV en WorkoutSession."""
        try:
            # Colonnes Samsung Health (peuvent varier selon la version de l'appli)
            activity_type = int(
                row.get("exercise_type", row.get("com.samsung.health.exercise.exercise_type", 0))
            )
            sport_type = ACTIVITY_MAP.get(activity_type, SportType.OTHER)

            # Timestamp (Samsung stocke en ms UTC)
            raw_start = row.get("start_time", row.get("com.samsung.health.exercise.start_time"))
            if pd.isna(raw_start):
                return None
            if isinstance(raw_start, int | float):
                start_dt = datetime.fromtimestamp(raw_start / 1000, tz=UTC)
            else:
                start_dt = pd.to_datetime(raw_start, utc=True).to_pydatetime()

            # Durée
            duration_ms = row.get("duration", row.get("com.samsung.health.exercise.duration", None))
            duration_min = float(duration_ms) / 60000 if pd.notna(duration_ms) else None

            # Distance
            distance_m = row.get("distance", row.get("com.samsung.health.exercise.distance", None))
            distance_km = float(distance_m) / 1000 if pd.notna(distance_m) else None

            # Calories
            calories = row.get("calorie", row.get("com.samsung.health.exercise.calorie", None))
            calories = int(float(calories)) if pd.notna(calories) else None

            # Fréquence cardiaque
            hr_mean = row.get(
                "mean_heart_rate", row.get("com.samsung.health.exercise.mean_heart_rate", None)
            )
            hr_max = row.get(
                "max_heart_rate", row.get("com.samsung.health.exercise.max_heart_rate", None)
            )

            # Allure moyenne (running)
            avg_pace = None
            if distance_km and duration_min and distance_km > 0:
                avg_pace = duration_min / distance_km

            return WorkoutSession(
                external_id=str(row.get("datauuid", f"samsung_{raw_start}")),
                sport_type=sport_type,
                date=start_dt,
                duration_minutes=duration_min,
                distance_km=distance_km,
                calories=calories,
                avg_heart_rate=int(float(hr_mean)) if pd.notna(hr_mean) else None,
                max_heart_rate=int(float(hr_max)) if pd.notna(hr_max) else None,
                avg_pace_min_km=avg_pace,
                source="samsung",
            )

        except Exception as e:
            logger.warning(f"Ligne ignorée : {e}")
            return None

    # ── Utilitaires DataFrame ─────────────────────────────────────────────────

    def to_dataframe(self, sessions: list[WorkoutSession]) -> pd.DataFrame:
        """Convertit une liste de WorkoutSession en DataFrame pour l'analyse."""
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
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def weekly_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Résumé hebdomadaire des séances pour le dashboard."""
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
