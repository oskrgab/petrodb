"""The Volve log pipeline builds ``petrophysical_interpretation.parquet`` from LAS pairs.

Runs the entry point end to end against a fixture raw directory of synthetic
LAS files (``log_fixtures``) and queries the Parquet it writes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from scripts.export.volve_logs import validator
from scripts.run_pipeline import volve_logs
from tests.volve.log_fixtures import (
    SENTINEL,
    WELLBORES,
    build_raw_tree,
    pair_paths,
    write_las,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
WELLS = REPO_ROOT / "parquet" / "volve" / "wells.parquet"
TABLE = "petrophysical_interpretation.parquet"


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    return build_raw_tree(tmp_path / "raw")


@pytest.fixture
def out(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    shutil.copy(WELLS, out / "wells.parquet")
    return out


@pytest.fixture
def built(raw: Path, out: Path) -> Path:
    volve_logs.run(raw_dir=raw, output_dir=out)
    return out / TABLE


def _rows(path: Path, sql: str) -> list[tuple]:
    return duckdb.sql(sql.format(t=f"'{path}'")).fetchall()


def test_one_row_per_depth_with_input_and_interpreted_curves_side_by_side(built: Path) -> None:
    rows = _rows(
        built,
        "SELECT depth_md, GR, RHOB, VSH, PHIF, COAL_FLAG FROM {t} "
        "WHERE source_wellbore = '15/9-F-1' ORDER BY depth_md",
    )
    assert rows == [
        (1000.1, None, 2.31, None, None, None),
        (1000.2, 50.0, 2.32, 0.5, 0.21, 0.0),
        (1000.3, 60.0, 2.33, 0.6, 0.22, 1.0),
        (1000.4, 70.0, 2.34, None, 0.23, 0.0),
        (1000.5, None, None, None, 0.24, 0.0),
    ]


def test_the_table_holds_the_eight_wellbores_each_with_its_npd_wellbore_code(built: Path) -> None:
    rows = _rows(
        built,
        "SELECT source_wellbore, npd_wellbore_code, count(*) FROM {t} GROUP BY ALL ORDER BY 1",
    )
    assert rows == [
        ("15/9-F-1", 7223, 5),
        ("15/9-F-1 A", 7224, 2),
        ("15/9-F-1 B", 7264, 2),
        ("15/9-F-1 C", 7405, 2),
        ("15/9-F-11 A", 7079, 2),
        ("15/9-F-11 B", 7080, 2),
        ("15/9-F-12", 5599, 3),
        ("15/9-F-15 D", 7289, 2),
    ]
    assert sorted(source for source, _, _ in rows) == sorted(s for s, _ in WELLBORES.values())


def test_rows_are_sorted_by_wellbore_then_depth(built: Path) -> None:
    keys = _rows(built, "SELECT npd_wellbore_code, source_wellbore, depth_md FROM {t}")
    assert keys == sorted(keys)
    assert len(set((s, d) for _, s, d in keys)) == len(keys)


def test_columns_are_the_key_then_the_source_mnemonics_unchanged_all_double(built: Path) -> None:
    columns = _rows(built, "SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM {t})")
    assert columns[:3] == [
        ("npd_wellbore_code", "BIGINT"),
        ("source_wellbore", "VARCHAR"),
        ("depth_md", "DOUBLE"),
    ]
    curves = dict(columns[3:])
    assert set(curves) == {"GR", "RHOB", "VSH", "PHIF", "COAL_FLAG", "SW", "KLOGH"}
    assert set(curves.values()) == {"DOUBLE"}


def test_no_sentinel_remains(built: Path) -> None:
    curves = ["GR", "RHOB", "VSH", "PHIF", "COAL_FLAG", "SW", "KLOGH"]
    hits = _rows(built, "SELECT count(*) FROM {t} WHERE " + " OR ".join(f"{c} = {SENTINEL}" for c in curves))
    assert hits == [(0,)]


def test_depth_is_rounded_to_four_decimals_at_the_source_depths(built: Path) -> None:
    rows = _rows(
        built,
        "SELECT depth_md, GR, KLOGH FROM {t} WHERE source_wellbore = '15/9-F-12' ORDER BY depth_md",
    )
    # KLOGH comes from the output file, not from the geomodel export (999).
    assert rows == [(3102.102, 90.0, 10.0), (3102.2544, 91.0, 20.0), (3102.4068, 92.0, 30.0)]


def test_one_command_builds_the_table(raw: Path, out: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "scripts.run_pipeline.volve_logs", str(raw), str(out)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    assert _rows(out / TABLE, "SELECT count(*) FROM {t}") == [(20,)]


# --- failure paths through the entry point --------------------------------


def test_a_shared_mnemonic_that_disagrees_stops_the_build(raw: Path, out: Path) -> None:
    write_las(
        pair_paths(raw, "15_9-F-1")[1],
        [1000.2, 1000.3],
        {"VSH": ("V/V", [0.5, 0.61])},
    )
    with pytest.raises(Exception, match=r"15/9-F-1\b.*VSH.*1000\.3"):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert not (out / TABLE).exists()


def test_a_wellbore_missing_from_wells_stops_the_build(raw: Path, out: Path) -> None:
    duckdb.sql(
        f"COPY (SELECT * FROM '{WELLS}' WHERE npd_wellbore_code <> 5599) "
        f"TO '{out / 'wells.parquet'}' (FORMAT parquet)"
    )
    with pytest.raises(validator.PrePublishCheckError, match=r"5599 \(15/9-F-12\)"):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert not (out / TABLE).exists()


def test_a_duplicate_depth_stops_the_build(raw: Path, out: Path) -> None:
    write_las(
        pair_paths(raw, "15_9-F-1 A")[0],
        [2000.0, 2000.1, 2000.1],
        {"GR": ("API", [80.0, 81.0, 82.0])},
    )
    with pytest.raises(validator.PrePublishCheckError, match=r"duplicate.*15/9-F-1 A.*2000\.1"):
        volve_logs.run(raw_dir=raw, output_dir=out)


def test_a_failed_build_keeps_the_previous_table(raw: Path, out: Path, built: Path) -> None:
    before = built.read_bytes()
    pair_paths(raw, "15_9-F-1 B")[1].unlink()
    with pytest.raises(Exception, match="WLC_PETRO_COMPUTED_OUTPUT_1.LAS"):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert built.read_bytes() == before


# --- each pre-publish check, on a written file ----------------------------


def _write(path: Path, rows: str) -> Path:
    duckdb.sql(
        "COPY (SELECT * FROM (VALUES " + rows + ") "
        "AS t(npd_wellbore_code, source_wellbore, depth_md, GR)) "
        f"TO '{path}' (FORMAT parquet)"
    )
    return path


GOOD_ROWS = "(7223, '15/9-F-1', 1000.1, 50.0), (7223, '15/9-F-1', 1000.2, 51.0)"


def test_a_well_formed_file_passes_every_check(tmp_path: Path) -> None:
    table = _write(tmp_path / "t.parquet", GOOD_ROWS)
    validator.check(table, WELLS, {"15/9-F-1": 2})


@pytest.mark.parametrize(
    ("rows", "expected", "message"),
    [
        (
            "(7223, '15/9-F-1', 1000.1, 50.0), (7223, '15/9-F-1', 1000.1, 51.0)",
            {"15/9-F-1": 2},
            r"duplicate key.*15/9-F-1 at 1000\.1",
        ),
        (
            "(1, '15/9-X', 1000.1, 50.0), (1, '15/9-X', 1000.2, 51.0)",
            {"15/9-X": 2},
            r"missing from wells: 1 \(15/9-X\)",
        ),
        (
            "(7223, '15/9-F-1', 1000.2, 50.0), (7223, '15/9-F-1', 1000.1, 51.0)",
            {"15/9-F-1": 2},
            r"does not strictly increase for 15/9-F-1: 1000\.1 m follows 1000\.2 m",
        ),
        (GOOD_ROWS, {"15/9-F-1": 3}, r"row count.*15/9-F-1: 2 rows, source has 3"),
        (
            "(7223, '15/9-F-1', 1000.1, 50.0), (7223, '15/9-F-1', 1000.2, -999.25)",
            {"15/9-F-1": 2},
            r"sentinel -999\.25 left in Curve GR: 15/9-F-1 at 1000\.2",
        ),
    ],
    ids=["duplicate-key", "not-in-wells", "depth-order", "row-count", "sentinel"],
)
def test_each_pre_publish_check_stops_the_build(
    tmp_path: Path, rows: str, expected: dict[str, int], message: str
) -> None:
    table = _write(tmp_path / "t.parquet", rows)
    with pytest.raises(validator.PrePublishCheckError, match=message):
        validator.check(table, WELLS, expected)


def test_the_built_parquet_is_gitignored() -> None:
    for name in (TABLE, f".{TABLE}.pending"):
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", f"parquet/volve/{name}"], cwd=REPO_ROOT
        )
        assert ignored.returncode == 0, name
