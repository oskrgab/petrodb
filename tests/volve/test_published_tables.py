"""Volve's published Parquet tables hold exactly what the SQLite source holds.

Replaces ``scripts/export/test_integration.py``, which looked for the tables at
the root of ``parquet/`` before they moved into ``parquet/volve/`` and renamed
the tracked database to test the exporter's missing-database error.
"""

from pathlib import Path
import sqlite3

import duckdb
import pytest

from scripts.export import parquet_export

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = REPO_ROOT / "parquet" / "volve"
SOURCE_DB = REPO_ROOT / "database" / "volve.db"


@pytest.mark.parametrize(
    ("table", "rows"),
    [("wells", 7), ("daily_production", 15634), ("monthly_production", 526)],
)
def test_published_table_has_every_source_row(table: str, rows: int) -> None:
    with sqlite3.connect(SOURCE_DB) as source:
        assert source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == rows
    published = PUBLISHED / f"{table}.parquet"
    assert duckdb.sql(f"SELECT COUNT(*) FROM '{published}'").fetchone()[0] == rows


def test_daily_production_joins_to_wells_on_npd_wellbore_code() -> None:
    unmatched = duckdb.sql(
        f"""
        SELECT COUNT(*)
        FROM '{PUBLISHED / "daily_production.parquet"}' d
        ANTI JOIN '{PUBLISHED / "wells.parquet"}' w USING (npd_wellbore_code)
        """
    ).fetchone()[0]
    assert unmatched == 0


def test_export_stops_when_the_source_database_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(parquet_export, "DATABASE_PATH", str(tmp_path / "volve.db"))
    with pytest.raises(SystemExit) as exit_info:
        parquet_export.main()
    assert exit_info.value.code != 0
    assert "Database not found" in capsys.readouterr().out
