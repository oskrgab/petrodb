"""The Volve log pipeline builds ``petrophysical_interpretation.parquet`` from LAS pairs.

Runs the entry point end to end against a fixture raw directory of synthetic
LAS files (``log_fixtures``) and queries the Parquet it writes. The output
directory holds the committed ``wells.parquet`` and a ``schema.json`` that
declares the fixture's columns with the committed declarations.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
import pytest

from scripts.export.volve_logs import schema_check, validator
from scripts.run_pipeline import volve_logs
from scripts.transform.volve_logs.interpretation_builder import CurveDisagreementError
from tests.volve.log_fixtures import (
    SENTINEL,
    WELLBORES,
    build_raw_tree,
    pair_paths,
    write_las,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
WELLS = REPO_ROOT / "parquet" / "volve" / "wells.parquet"
SCHEMA = REPO_ROOT / "parquet" / "volve" / "schema.json"
TABLE = "petrophysical_interpretation.parquet"

# GR: all eight Wellbores; SW: the six plain pairs; the rest one each, by
# mnemonic. VSH is in both files of 15/9-F-1 and counts once.
FIXTURE_COLUMNS = [
    "npd_wellbore_code", "source_wellbore", "depth_md",
    "GR", "SW", "COAL_FLAG", "KLOGH", "PHIF", "RHOB", "VSH",
]  # fmt: skip


def _write_schema(path: Path, columns: list[dict]) -> None:
    path.write_text(
        json.dumps({"tables": {"petrophysical_interpretation": {"columns": columns}}})
    )


def _fixture_schema() -> list[dict]:
    """The committed declarations of the fixture's columns, in the fixture's order."""
    committed = json.loads(SCHEMA.read_text())["tables"]["petrophysical_interpretation"]
    by_name = {c["name"]: c for c in committed["columns"]}
    return [by_name[name] for name in FIXTURE_COLUMNS]


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    return build_raw_tree(tmp_path / "raw")


@pytest.fixture
def out(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    shutil.copy(WELLS, out / "wells.parquet")
    _write_schema(out / "schema.json", _fixture_schema())
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


def test_curves_are_ordered_by_how_many_wellbores_carry_them_ties_by_mnemonic(
    built: Path,
) -> None:
    columns = [name for name, *_ in _rows(built, "DESCRIBE SELECT * FROM {t}")]
    assert columns == FIXTURE_COLUMNS


def test_the_table_is_one_row_group(built: Path) -> None:
    assert _rows(built, "SELECT num_row_groups FROM parquet_file_metadata({t})") == [(1,)]


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
    with pytest.raises(CurveDisagreementError, match=r"15/9-F-1\b.*VSH.*1000\.3"):
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


def _drop_sw(columns: list[dict]) -> None:
    columns.remove(next(c for c in columns if c["name"] == "SW"))


def _swap_gr_and_sw(columns: list[dict]) -> None:
    columns[3], columns[4] = columns[4], columns[3]


def _declare(column: str, **changes: object):
    def change(columns: list[dict]) -> None:
        next(c for c in columns if c["name"] == column).update(changes)

    return change


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (_drop_sw, r"columns are .*SW.*; schema\.json declares"),
        (_swap_gr_and_sw, r"columns are .*GR, SW.*; schema\.json declares .*SW, GR"),
        (_declare("SW", name="SWT"), r"columns are .*SW.*; schema\.json declares .*SWT"),
        (_declare("GR", type="TEXT"), r"GR: DOUBLE in the file, schema\.json declares TEXT"),
        (
            _declare("npd_wellbore_code", type="DOUBLE"),
            r"npd_wellbore_code: BIGINT in the file, schema\.json declares DOUBLE",
        ),
        (_declare("GR", not_null=True), r"GR: holds NULL, schema\.json declares NOT NULL"),
    ],
    ids=["missing-column", "order", "name", "type", "key-type", "nullability"],
)
def test_output_that_differs_from_schema_json_stops_the_build(
    raw: Path, out: Path, change, message: str
) -> None:
    columns = _fixture_schema()
    change(columns)
    _write_schema(out / "schema.json", columns)
    with pytest.raises(schema_check.SchemaMismatchError, match=message):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert not (out / TABLE).exists()


def test_a_column_the_file_requires_but_schema_json_declares_nullable_is_a_mismatch(
    tmp_path: Path,
) -> None:
    # DuckDB writes every column optional; another writer may not.
    rows = pq.read_table(_write(tmp_path / "one.parquet", GOOD_ROWS))
    required = rows.schema.set(3, rows.schema.field("GR").with_nullable(False))
    table = tmp_path / "t.parquet"
    pq.write_table(rows.cast(required), table)
    schema = tmp_path / "schema.json"
    _write_schema(schema, [c for c in _fixture_schema() if c["name"] in rows.column_names])
    with pytest.raises(
        schema_check.SchemaMismatchError,
        match=r"GR: required in the file, schema\.json declares it nullable",
    ):
        schema_check.check(table, schema)


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


def test_a_file_of_more_than_one_row_group_stops_the_build(tmp_path: Path) -> None:
    # DuckDB will not split two rows into row groups; pyarrow will.
    rows = pq.read_table(_write(tmp_path / "one.parquet", GOOD_ROWS))
    table = tmp_path / "t.parquet"
    pq.write_table(rows, table, row_group_size=1)
    with pytest.raises(validator.PrePublishCheckError, match=r"2 row groups"):
        validator.check(table, WELLS, {"15/9-F-1": 2})


def test_columns_out_of_the_declared_order_stop_the_build(tmp_path: Path) -> None:
    # SW is carried by two Wellbores, GR by one: SW must come first.
    table = tmp_path / "t.parquet"
    duckdb.sql(
        "COPY (SELECT * FROM (VALUES "
        "(7223, '15/9-F-1', 1000.1, 50.0, 0.9), (7224, '15/9-F-1 A', 2000.0, NULL, 0.8)"
        ") AS t(npd_wellbore_code, source_wellbore, depth_md, GR, SW)) "
        f"TO '{table}' (FORMAT parquet)"
    )
    with pytest.raises(
        validator.PrePublishCheckError,
        match=r"column order.*npd_wellbore_code, source_wellbore, depth_md, SW, GR",
    ):
        validator.check(table, WELLS, {"15/9-F-1": 1, "15/9-F-1 A": 1})


def test_the_built_parquet_is_gitignored() -> None:
    for name in (TABLE, f".{TABLE}.pending"):
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", f"parquet/volve/{name}"], cwd=REPO_ROOT
        )
        assert ignored.returncode == 0, name
