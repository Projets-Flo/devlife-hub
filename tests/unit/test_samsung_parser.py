"""
Tests unitaires du parser Samsung Health.
Lance avec : pytest tests/unit/test_samsung_parser.py -v
"""

import io
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.sport.parsers.samsung_health import ACTIVITY_MAP, SamsungHealthParser


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_CSV = """datauuid,exercise_type,start_time,duration,distance,calorie,mean_heart_rate,max_heart_rate
abc123,1001,1710000000000,3600000,10500,550,148,172
def456,10001,1710100000000,4200000,,380,135,165
"""


@pytest.fixture
def parser(tmp_path: Path) -> SamsungHealthParser:
    return SamsungHealthParser(export_dir=tmp_path)


@pytest.fixture
def sample_csv_file(tmp_path: Path) -> Path:
    f = tmp_path / "com.samsung.shealth.exercise.2024.csv"
    f.write_text(SAMPLE_CSV)
    return f


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestActivityMap:
    def test_running_mapped(self):
        assert ACTIVITY_MAP[1001] == "running"

    def test_strength_mapped(self):
        assert ACTIVITY_MAP[10001] == "strength"


class TestSamsungHealthParser:

    def test_parse_workouts_no_files(self, parser: SamsungHealthParser):
        """Sans fichier, retourne une liste vide sans erreur."""
        sessions = parser.parse_workouts()
        assert sessions == []

    def test_parse_running_session(self, parser: SamsungHealthParser, sample_csv_file: Path):
        sessions = parser.parse_workouts()
        assert len(sessions) == 2

        run = sessions[0]
        assert run.sport_type == "running"
        assert abs(run.duration_minutes - 60.0) < 0.1
        assert abs(run.distance_km - 10.5) < 0.01
        assert run.calories == 550
        assert run.avg_heart_rate == 148
        assert run.source == "samsung"

    def test_parse_strength_session(self, parser: SamsungHealthParser, sample_csv_file: Path):
        sessions = parser.parse_workouts()
        strength = sessions[1]
        assert strength.sport_type == "strength"
        assert strength.distance_km is None   # pas de distance en muscu

    def test_to_dataframe(self, parser: SamsungHealthParser, sample_csv_file: Path):
        sessions = parser.parse_workouts()
        df = parser.to_dataframe(sessions)

        assert len(df) == 2
        assert "distance_km" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert df["date"].is_monotonic_increasing   # trié par date

    def test_weekly_summary(self, parser: SamsungHealthParser, sample_csv_file: Path):
        sessions = parser.parse_workouts()
        df = parser.to_dataframe(sessions)
        summary = parser.weekly_summary(df)

        assert "week" in summary.columns
        assert "sessions" in summary.columns
        assert summary["sessions"].sum() == 2
