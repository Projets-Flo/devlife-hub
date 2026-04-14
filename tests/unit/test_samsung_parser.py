"""
Tests unitaires du parser Samsung Health.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.common.database import SportType
from src.sport.parsers.samsung_health import ACTIVITY_MAP, SamsungHealthParser

SAMPLE_CSV = (
    "com.samsung.shealth.exercise,2,1\n"
    "com.samsung.health.exercise.datauuid,"
    "com.samsung.health.exercise.exercise_type,"
    "com.samsung.health.exercise.start_time,"
    "com.samsung.health.exercise.duration,"
    "com.samsung.health.exercise.distance,"
    "com.samsung.health.exercise.calorie,"
    "com.samsung.health.exercise.mean_heart_rate,"
    "com.samsung.health.exercise.max_heart_rate,"
    "com.samsung.health.exercise.mean_speed,"
    "com.samsung.health.exercise.pkg_name\n"
    "abc123,1002,2024-01-15 08:00:00.000,3600000,10000,500,148,172,2.778,"
    "com.sec.android.app.shealth\n"
    "def456,1002,2024-01-16 09:00:00.000,1800000,5000,250,155,180,2.778,"
    "com.sec.android.app.shealth\n"
)


@pytest.fixture
def parser_with_data(tmp_path: Path) -> SamsungHealthParser:
    """Crée le CSV puis le parser — ordre garanti."""
    sub = tmp_path / "samsunghealth"
    sub.mkdir()
    f = sub / "com.samsung.shealth.exercise.20240101000000.csv"
    f.write_text(SAMPLE_CSV)
    return SamsungHealthParser(export_dir=tmp_path)


@pytest.fixture
def parser_empty(tmp_path: Path) -> SamsungHealthParser:
    return SamsungHealthParser(export_dir=tmp_path)


class TestActivityMap:
    def test_running_mapped(self):
        assert ACTIVITY_MAP[1002] == SportType.RUNNING

    def test_only_running_in_map(self):
        assert len(ACTIVITY_MAP) == 1


class TestSamsungHealthParser:
    def test_parse_workouts_no_files(self, parser_empty: SamsungHealthParser):
        sessions = parser_empty.parse_workouts()
        assert sessions == []

    def test_parse_running_sessions(self, parser_with_data: SamsungHealthParser):
        sessions = parser_with_data.parse_workouts()
        assert len(sessions) == 2

    def test_running_session_data(self, parser_with_data: SamsungHealthParser):
        sessions = parser_with_data.parse_workouts()
        run = sessions[0]
        assert run.sport_type == SportType.RUNNING
        assert abs(run.duration_minutes - 60.0) < 0.1
        assert abs(run.distance_km - 10.0) < 0.01
        assert run.calories == 500
        assert run.avg_heart_rate == 148
        assert run.source == "samsung"

    def test_to_dataframe(self, parser_with_data: SamsungHealthParser):
        sessions = parser_with_data.parse_workouts()
        df = parser_with_data.to_dataframe(sessions)
        assert len(df) == 2
        assert "distance_km" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert df["date"].is_monotonic_increasing

    def test_stats_running(self, parser_with_data: SamsungHealthParser):
        sessions = parser_with_data.parse_workouts()
        df = parser_with_data.to_dataframe(sessions)
        stats = parser_with_data.stats_running(df)
        assert stats["total_sessions"] == 2
        assert abs(stats["total_km"] - 15.0) < 0.1
