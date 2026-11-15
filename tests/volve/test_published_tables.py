"""Volve's published Parquet tables hold exactly what the SQLite source holds.

Replaces ``scripts/export/test_integration.py``, which looked for the tables at
the root of ``parquet/`` before they moved into ``parquet/volve/`` and renamed
the tracked database to test the exporter's missing-database error.

``wells`` lists every Wellbore the public register assigns to Volve, joined to
the production source; the seven with production keep what they had before.
"""

from pathlib import Path
import sqlite3

import duckdb
import pytest

from scripts.export import parquet_export

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = REPO_ROOT / "parquet" / "volve"
SOURCE_DB = REPO_ROOT / "database" / "volve.db"
WELLS = PUBLISHED / "wells.parquet"
PRODUCTION_TABLES = ("daily_production", "monthly_production")

# The seven producing Wellbores as wells.parquet published them before it
# grew to every Volve Wellbore in the register: nothing here may change.
PRODUCING_WELLBORES = [
    (5351, "NO 15/9-F-14 H", "15/9-F-14", 3420717, "VOLVE", 369304, "MÆRSK INSPIRER"),
    (5599, "NO 15/9-F-12 H", "15/9-F-12", 3420717, "VOLVE", 369304, "MÆRSK INSPIRER"),
    (5693, "NO 15/9-F-4 AH", "15/9-F-4", 3420717, "VOLVE", 369304, "MÆRSK INSPIRER"),
    (5769, "NO 15/9-F-5 AH", "15/9-F-5", 3420717, "VOLVE", 369304, "MÆRSK INSPIRER"),
    (7078, "NO 15/9-F-11 H", "15/9-F-11", 3420717, "VOLVE", 369304, "MÆRSK INSPIRER"),
    (7289, "NO 15/9-F-15 D", "15/9-F-15 D", 3420717, "VOLVE", 369304, "MÆRSK INSPIRER"),
    (7405, "NO 15/9-F-1 C", "15/9-F-1 C", 3420717, "VOLVE", 369304, "MÆRSK INSPIRER"),
]
# Every column wells had before, with its published Parquet type.
EXISTING_COLUMNS = {
    "npd_wellbore_code": "BIGINT",
    "wellbore_code": "VARCHAR",
    "wellbore_name": "VARCHAR",
    "npd_field_code": "BIGINT",
    "npd_field_name": "VARCHAR",
    "npd_facility_code": "BIGINT",
    "npd_facility_name": "VARCHAR",
}


@pytest.mark.parametrize(
    ("table", "rows"),
    [("wells", 27), ("daily_production", 15634), ("monthly_production", 526)],
)
def test_published_table_has_every_source_row(table: str, rows: int) -> None:
    with sqlite3.connect(SOURCE_DB) as source:
        assert source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == rows
    published = PUBLISHED / f"{table}.parquet"
    assert duckdb.sql(f"SELECT COUNT(*) FROM '{published}'").fetchone()[0] == rows


@pytest.mark.parametrize("table", PRODUCTION_TABLES)
def test_production_joins_to_wells_on_npd_wellbore_code(table: str) -> None:
    unmatched = duckdb.sql(
        f"""
        SELECT COUNT(*)
        FROM '{PUBLISHED / f"{table}.parquet"}' p
        ANTI JOIN '{WELLS}' w USING (npd_wellbore_code)
        """
    ).fetchone()[0]
    assert unmatched == 0


def test_wells_lists_every_volve_wellbore_once() -> None:
    rows, keys = duckdb.sql(
        f"SELECT COUNT(*), COUNT(DISTINCT npd_wellbore_code) FROM '{WELLS}'"
    ).fetchone()
    assert (rows, keys) == (27, 27)


def test_producing_wellbores_keep_their_published_values_and_types() -> None:
    columns = ", ".join(EXISTING_COLUMNS)
    relation = duckdb.sql(
        f"""
        SELECT {columns} FROM '{WELLS}'
        WHERE npd_wellbore_code IN
              (SELECT npd_wellbore_code FROM '{PUBLISHED / "daily_production.parquet"}')
        ORDER BY npd_wellbore_code
        """
    )
    assert dict(zip(relation.columns, map(str, relation.types))) == EXISTING_COLUMNS
    assert relation.fetchall() == PRODUCING_WELLBORES


def test_has_production_marks_exactly_the_wellbores_with_production_rows() -> None:
    produced = " UNION ".join(
        f"SELECT npd_wellbore_code FROM '{PUBLISHED / f'{t}.parquet'}'"
        for t in PRODUCTION_TABLES
    )
    flags = dict(
        duckdb.sql(f"SELECT npd_wellbore_code, has_production FROM '{WELLS}'").fetchall()
    )
    assert None not in flags.values()
    flagged = {code for code, flag in flags.items() if flag is True}
    assert flagged == {r[0] for r in duckdb.sql(produced).fetchall()}
    assert flagged == {r[0] for r in PRODUCING_WELLBORES}


def test_every_parent_wellbore_is_a_row_of_wells() -> None:
    orphans = duckdb.sql(
        f"""
        SELECT c.wellbore_name FROM '{WELLS}' c
        ANTI JOIN '{WELLS}' p ON c.parent_npd_wellbore_code = p.npd_wellbore_code
        WHERE c.parent_npd_wellbore_code IS NOT NULL
        """
    ).fetchall()
    assert orphans == []


def test_register_columns_for_a_producer_an_undrilled_and_an_exploration_wellbore() -> None:
    # From the register snapshot: 15/9-F-1 C is a sidetrack of 15/9-F-1 B
    # completed in 2014 to produce oil; 15/9-F-10 B was never drilled;
    # 15/9-19 A is an appraisal sidetrack of the discovery well 15/9-19 S.
    rows = {
        r[0]: r[1:]
        for r in duckdb.sql(
            f"""
            SELECT c.wellbore_name, c.wellbore_type, c.purpose, c.content,
                   c.completion_year, p.wellbore_name, c.wellbore_code,
                   c.npd_facility_code, c.npd_field_name
            FROM '{WELLS}' c
            LEFT JOIN '{WELLS}' p ON c.parent_npd_wellbore_code = p.npd_wellbore_code
            WHERE c.wellbore_name IN ('15/9-F-1 C', '15/9-F-10 B', '15/9-19 A', '15/9-19 S')
            """
        ).fetchall()
    }
    assert rows == {
        "15/9-F-1 C": ("DEVELOPMENT", "PRODUCTION", "OIL", 2014, "15/9-F-1 B",
                       "NO 15/9-F-1 C", 369304, "VOLVE"),
        "15/9-F-10 B": ("DEVELOPMENT", "PRODUCTION", None, None, "15/9-F-10 A",
                        None, None, "VOLVE"),
        "15/9-19 A": ("EXPLORATION", "APPRAISAL", "OIL", 1997, "15/9-19 S",
                      None, None, "VOLVE"),
        "15/9-19 S": ("EXPLORATION", "WILDCAT", "DRY", 1993, None,
                      None, None, "VOLVE"),
    }


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
