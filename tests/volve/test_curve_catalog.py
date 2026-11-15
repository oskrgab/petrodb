"""The Volve log pipeline writes the Curve catalog, ``log_curves.parquet``, beside the table.

Runs the entry point end to end against the fixture raw directory of synthetic
LAS files (``log_fixtures``) and queries the catalog it writes.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import duckdb
import pytest

from scripts.export.volve_logs import catalog_check, validator
from scripts.run_pipeline import volve_logs
from tests.volve.log_fixtures import build_raw_tree, fixture_schema, pair_paths, write_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
WELLS = REPO_ROOT / "parquet" / "volve" / "wells.parquet"
TABLE = "petrophysical_interpretation"
CATALOG = "log_curves.parquet"

INPUT_FILE = "Well_logs_pr_WELL/{}/05.PETROPHYSICAL INTERPRETATION/WLC_PETRO_COMPUTED_INPUT_1.LAS"
OUTPUT_FILE = "Well_logs_pr_WELL/{}/05.PETROPHYSICAL INTERPRETATION/WLC_PETRO_COMPUTED_OUTPUT_1.LAS"


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    return build_raw_tree(tmp_path / "raw")


@pytest.fixture
def out(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    shutil.copy(WELLS, out / "wells.parquet")
    write_schema(out / "schema.json", fixture_schema())
    return out


@pytest.fixture
def built(raw: Path, out: Path) -> Path:
    volve_logs.run(raw_dir=raw, output_dir=out)
    return out / CATALOG


def _rows(path: Path, sql: str) -> list[tuple]:
    return duckdb.sql(sql.format(t=f"'{path}'")).fetchall()


def _pair_rows(code: int, source: str, folder: str) -> list[tuple]:
    """The two catalog rows of each plain fixture pair: GR in, SW out."""
    return [
        (TABLE, code, source, "GR", "input", "gAPI", "API", 2000.0, 2000.1, 2,
         INPUT_FILE.format(folder)),
        (TABLE, code, source, "SW", "interpreted", "v/v", "v/v", 2000.1, 2000.1, 1,
         OUTPUT_FILE.format(folder)),
    ]  # fmt: skip


def test_the_catalog_has_one_row_per_source_wellbore_and_curve_with_data(built: Path) -> None:
    rows = _rows(built, "SELECT * FROM {t}")
    f1, t2, top = "15_9-F-1", "15_9-F-11 T2", "15_9-F-11"
    a, bt2, sr = (
        "Well_logs_pr_WELL/15_9-19 A/05.PETROPHYSICAL INTERPRETATION/CPI/15_9-19_A_CPI.las",
        "Well_logs_pr_WELL/15_9-19 B&BT2/05.PETROPHYSICAL INTERPRETATION/CPI/15_9-19_BT2_CPI.las",
        "Well_logs_pr_WELL/15_9-19 S&SR/05.PETROPHYSICAL INTERPRETATION/CPI/15_9-19_SR_CPI.las",
    )
    assert rows == [
        # The 15/9-19 wellbores: one file holds both kinds of Curve, and the
        # committed list classifies them. BT2 takes 15/9-19 B's code.
        (TABLE, 2105, "15/9-19 SR", "DT", "input", "µs/ft", "", 3549.7008, 3549.8532, 2, sr),
        (TABLE, 2105, "15/9-19 SR", "SW", "interpreted", "v/v", "V/V", 3549.7008, 3549.7008, 1,
         sr),
        (TABLE, 3145, "15/9-19 A", "BS", "input", "in", "IN", 3666.5916, 3666.744, 2, a),
        (TABLE, 3145, "15/9-19 A", "PHIF", "interpreted", "v/v", "V/V", 3666.5916, 3666.5916, 1,
         a),
        (TABLE, 3145, "15/9-19 A", "TEMP", "interpreted", "°C", "DEGC", 3666.5916, 3666.744, 2,
         a),
        (TABLE, 3251, "15/9-19 BT2", "KLOGV", "interpreted", "mD", "MD", 3768.09, 3768.2424, 2,
         bt2),
        (TABLE, 3251, "15/9-19 BT2", "PHIF", "interpreted", "v/v", "V/V", 3768.09, 3768.2424, 2,
         bt2),
        # 15/9-F-12 (5599): KLOGH from the output file, not the geomodel export.
        (TABLE, 5599, "15/9-F-12", "GR", "input", "gAPI", "API", 3102.102, 3102.4068, 3,
         INPUT_FILE.format("15_9-F-12")),
        (TABLE, 5599, "15/9-F-12", "KLOGH", "interpreted", "mD", "mD", 3102.102, 3102.4068, 3,
         OUTPUT_FILE.format("15_9-F-12")),
        # The top-hole section and the Technical sidetrack share 15/9-F-11's code.
        # The top-hole section's ROP has one sample; its all-sentinel 200.2 m is gone.
        (TABLE, 7078, "15/9-F-11", "GR", "input", "gAPI", "API", 200.0, 200.1, 2,
         INPUT_FILE.format(top)),
        (TABLE, 7078, "15/9-F-11", "ROP", "input", "m/h", "m/hr", 200.0, 200.0, 1,
         INPUT_FILE.format(top)),
        (TABLE, 7078, "15/9-F-11 T2", "GR", "input", "gAPI", "API", 200.0, 4000.0, 4,
         INPUT_FILE.format(t2)),
        (TABLE, 7078, "15/9-F-11 T2", "PHIF", "interpreted", "v/v", "v/v", 4000.0, 4000.0, 1,
         OUTPUT_FILE.format(t2)),
        *_pair_rows(7079, "15/9-F-11 A", "15_9-F-11 A"),
        *_pair_rows(7080, "15/9-F-11 B", "15_9-F-11 B"),
        # 15/9-F-1: sentinels are not samples; VSH is in both files, so it is
        # an Input curve named after the input file and its spelling there.
        (TABLE, 7223, "15/9-F-1", "COAL_FLAG", "interpreted", "unitless", "unitless",
         1000.2, 1000.5, 4, OUTPUT_FILE.format(f1)),
        (TABLE, 7223, "15/9-F-1", "GR", "input", "gAPI", "API", 1000.2, 1000.4, 3,
         INPUT_FILE.format(f1)),
        (TABLE, 7223, "15/9-F-1", "PHIF", "interpreted", "v/v", "V/V", 1000.2, 1000.5, 4,
         OUTPUT_FILE.format(f1)),
        (TABLE, 7223, "15/9-F-1", "RHOB", "input", "g/cm³", "g/cm3", 1000.1, 1000.4, 4,
         INPUT_FILE.format(f1)),
        (TABLE, 7223, "15/9-F-1", "VSH", "input", "v/v", "v/v", 1000.2, 1000.3, 2,
         INPUT_FILE.format(f1)),
        *_pair_rows(7224, "15/9-F-1 A", "15_9-F-1 A"),
        *_pair_rows(7264, "15/9-F-1 B", "15_9-F-1 B"),
        *_pair_rows(7289, "15/9-F-15 D", "15_9-F-15 D"),
        *_pair_rows(7405, "15/9-F-1 C", "15_9-F-1 C"),
    ]  # fmt: skip


def test_the_catalog_columns_and_types(built: Path) -> None:
    columns = _rows(built, "SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM {t})")
    assert columns == [
        ("table_name", "VARCHAR"),
        ("npd_wellbore_code", "BIGINT"),
        ("source_wellbore", "VARCHAR"),
        ("mnemonic", "VARCHAR"),
        ("curve_kind", "VARCHAR"),
        ("unit", "VARCHAR"),
        ("source_unit", "VARCHAR"),
        ("first_depth_md", "DOUBLE"),
        ("last_depth_md", "DOUBLE"),
        ("sample_count", "BIGINT"),
        ("source_file", "VARCHAR"),
    ]


def test_every_source_file_exists_in_the_raw_directory(raw: Path, built: Path) -> None:
    files = _rows(built, "SELECT DISTINCT source_file FROM {t}")
    assert files
    for (name,) in files:
        assert (raw / name).is_file(), name


def test_the_catalog_agrees_with_the_table_it_describes(out: Path, built: Path) -> None:
    table = out / f"{TABLE}.parquet"
    curves = [
        name
        for (name,) in _rows(table, "SELECT column_name FROM (DESCRIBE SELECT * FROM {t})")[3:]
    ]
    from_table = sorted(
        row
        for curve in curves
        for row in duckdb.sql(
            f'SELECT source_wellbore, \'{curve}\', min(depth_md), max(depth_md), count("{curve}") '
            f"FROM '{table}' WHERE \"{curve}\" IS NOT NULL GROUP BY ALL"
        ).fetchall()
    )
    from_catalog = _rows(
        built,
        "SELECT source_wellbore, mnemonic, first_depth_md, last_depth_md, sample_count "
        "FROM {t} ORDER BY source_wellbore, mnemonic",
    )
    assert from_catalog == from_table


def test_a_failed_build_writes_no_catalog_and_keeps_the_previous_one(
    raw: Path, out: Path, built: Path
) -> None:
    before = built.read_bytes()
    pair_paths(raw, "15_9-F-1 A")[0].unlink()
    with pytest.raises(Exception, match="WLC_PETRO_COMPUTED_INPUT_1.LAS"):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert built.read_bytes() == before
    assert not (out / f".{CATALOG}.pending").exists()


def test_the_built_catalog_is_gitignored() -> None:
    for name in (CATALOG, f".{CATALOG}.pending"):
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", f"parquet/volve/{name}"], cwd=REPO_ROOT
        )
        assert ignored.returncode == 0, name


# --- each catalog check, on written files ----------------------------------

# A written table: 15/9-F-1 has GR at two depths and RHOB at one.
TABLE_ROWS = (
    "(7223, '15/9-F-1', 1000.1, 50.0, NULL), (7223, '15/9-F-1', 1000.2, 51.0, 2.3)"
)
GR_ROW = (
    f"('{TABLE}', 7223, '15/9-F-1', 'GR', 'input', 'gAPI', 'API', 1000.1, 1000.2, 2, 'in.LAS')"
)
RHOB_ROW = (
    f"('{TABLE}', 7223, '15/9-F-1', 'RHOB', 'input', 'g/cm³', 'g/cm3', 1000.2, 1000.2, 1, 'in.LAS')"
)


def _write_table(path: Path) -> Path:
    duckdb.sql(
        f"COPY (SELECT * REPLACE (depth_md::DOUBLE AS depth_md) FROM (VALUES {TABLE_ROWS}) "
        "AS t(npd_wellbore_code, source_wellbore, depth_md, GR, RHOB)) "
        f"TO '{path}' (FORMAT parquet)"
    )
    return path


def _write_catalog(path: Path, rows: list[str]) -> Path:
    duckdb.sql(
        "COPY (SELECT * REPLACE (first_depth_md::DOUBLE AS first_depth_md, "
        "last_depth_md::DOUBLE AS last_depth_md) FROM (VALUES " + ", ".join(rows) + ") AS t(table_name, "
        "npd_wellbore_code, source_wellbore, mnemonic, curve_kind, unit, source_unit, "
        "first_depth_md, last_depth_md, sample_count, source_file)) "
        f"TO '{path}' (FORMAT parquet)"
    )
    return path


def test_a_catalog_that_agrees_with_its_table_passes(tmp_path: Path) -> None:
    table = _write_table(tmp_path / "t.parquet")
    catalog = _write_catalog(tmp_path / "c.parquet", [GR_ROW, RHOB_ROW])
    catalog_check.check(catalog, {TABLE: table}, WELLS)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([GR_ROW, RHOB_ROW, RHOB_ROW], r"duplicate.*petrophysical_interpretation, 15/9-F-1, RHOB appears 2"),
        (
            [GR_ROW, RHOB_ROW.replace("7223", "1")],
            r"npd_wellbore_code missing from wells: 1 \(15/9-F-1\)",
        ),
        (
            [GR_ROW, RHOB_ROW, RHOB_ROW.replace(f"'{TABLE}'", "'composite'")],
            r"names a table the build did not write: composite",
        ),
        ([GR_ROW], r"disagrees.*15/9-F-1 RHOB: has data, but no catalog row"),
        (
            [GR_ROW, RHOB_ROW, GR_ROW.replace("'GR'", "'PHIF'")],
            r"15/9-F-1 PHIF: catalog row, but no data in the table",
        ),
        (
            [GR_ROW.replace("1000.2, 2,", "1000.2, 3,"), RHOB_ROW],
            r"15/9-F-1 GR: table has .* \(7223, 1000\.1, 1000\.2, 2\), "
            r"catalog has \(7223, 1000\.1, 1000\.2, 3\)",
        ),
        (
            [GR_ROW.replace("1000.1, 1000.2", "1000.0, 1000.2"), RHOB_ROW],
            r"15/9-F-1 GR: .*catalog has \(7223, 1000\.0, 1000\.2, 2\)",
        ),
        (
            [GR_ROW, RHOB_ROW.replace("1000.2, 1000.2", "1000.2, 1000.3")],
            r"15/9-F-1 RHOB: .*catalog has \(7223, 1000\.2, 1000\.3, 1\)",
        ),
        (
            [GR_ROW.replace("7223", "7224"), RHOB_ROW],
            r"15/9-F-1 GR: table has .* \(7223, .*catalog has \(7224,",
        ),
    ],
    ids=[
        "duplicate-key",
        "not-in-wells",
        "unknown-table",
        "missing-row",
        "row-without-data",
        "sample-count",
        "first-depth",
        "last-depth",
        "wellbore-code",
    ],
)
def test_each_catalog_check_stops_the_build(tmp_path: Path, rows: list[str], message: str) -> None:
    table = _write_table(tmp_path / "t.parquet")
    catalog = _write_catalog(tmp_path / "c.parquet", rows)
    with pytest.raises(validator.PrePublishCheckError, match=message):
        catalog_check.check(catalog, {TABLE: table}, WELLS)
