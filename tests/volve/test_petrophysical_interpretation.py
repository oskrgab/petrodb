"""The Volve log pipeline builds ``petrophysical_interpretation.parquet`` from LAS and DLIS pairs.

Runs the entry point end to end against a fixture raw directory of synthetic
LAS and DLIS files (``log_fixtures``) and queries the Parquet it writes.
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
from scripts.transform.volve_logs.interpretation_builder import CurveDisagreementError
from scripts.transform.volve_logs.sources import SourceFileError
from scripts.transform.volve_logs.units import UnitMismatchError, UnitSpellingError
from tests.volve.log_fixtures import (
    DLIS_WELLBORES,
    SENTINEL,
    TECHNICAL_SIDETRACK,
    TOP_HOLE,
    WELLBORES,
    build_raw_tree,
    dlis_pair_paths,
    pair_paths,
    write_dlis,
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


def test_two_spellings_of_one_unit_make_one_column_with_the_values_unchanged(
    raw: Path, out: Path
) -> None:
    # 15/9-F-1 spells VSH's fraction v/v in the input file and V/V in the
    # output file; 15/9-F-1 A spells GR's API units API and its SW v/v_decimal.
    write_las(pair_paths(raw, "15_9-F-1 A")[1], [2000.1], {"SW": ("v/v_decimal", [0.9])})
    volve_logs.run(raw_dir=raw, output_dir=out)
    rows = _rows(
        out / TABLE,
        "SELECT source_wellbore, depth_md, VSH, SW FROM {t} "
        "WHERE source_wellbore IN ('15/9-F-1', '15/9-F-1 A') ORDER BY ALL",
    )
    assert rows == [
        ("15/9-F-1", 1000.1, None, None),
        ("15/9-F-1", 1000.2, 0.5, None),
        ("15/9-F-1", 1000.3, 0.6, None),
        ("15/9-F-1", 1000.4, None, None),
        ("15/9-F-1", 1000.5, None, None),
        ("15/9-F-1 A", 2000.0, None, None),
        ("15/9-F-1 A", 2000.1, None, 0.9),
    ]


def test_the_table_holds_every_source_each_with_its_npd_wellbore_code(built: Path) -> None:
    rows = _rows(
        built,
        "SELECT source_wellbore, npd_wellbore_code, count(*) FROM {t} GROUP BY ALL ORDER BY 1",
    )
    assert rows == [
        ("15/9-F-1", 7223, 5),
        ("15/9-F-1 A", 7224, 2),
        ("15/9-F-1 B", 7264, 2),
        ("15/9-F-1 C", 7405, 2),
        ("15/9-F-10", 6099, 3),
        ("15/9-F-11", 7078, 2),
        ("15/9-F-11 A", 7079, 2),
        ("15/9-F-11 B", 7080, 2),
        ("15/9-F-11 T2", 7078, 4),
        ("15/9-F-12", 5599, 3),
        ("15/9-F-14", 5351, 2),
        ("15/9-F-15", 6184, 1),
        ("15/9-F-15 A", 5785, 2),
        ("15/9-F-15 B", 6046, 2),
        ("15/9-F-15 C", 5794, 2),
        ("15/9-F-15 D", 7289, 2),
        ("15/9-F-4", 5693, 2),
        ("15/9-F-5", 5769, 2),
    ]
    assert sorted(source for source, _, _ in rows) == sorted(
        [s for s, _ in WELLBORES.values()]
        + [s for s, _ in DLIS_WELLBORES.values()]
        + [TECHNICAL_SIDETRACK[1], TOP_HOLE[1]]
    )


def test_a_technical_sidetrack_takes_its_parent_wellbores_code_and_keeps_its_name(
    built: Path,
) -> None:
    rows = _rows(
        built,
        "SELECT npd_wellbore_code, depth_md, GR, PHIF FROM {t} "
        "WHERE source_wellbore = '15/9-F-11 T2' ORDER BY depth_md",
    )
    # 7078 is 15/9-F-11 in the register; T2 has no code of its own.
    assert rows == [
        (7078, 200.0, 40.0, None),
        (7078, 200.1, 41.0, None),
        (7078, 200.2, 42.0, None),
        (7078, 4000.0, 43.0, 0.2),
    ]


def test_the_input_only_top_hole_section_is_its_own_source_with_no_interpreted_curve(
    built: Path,
) -> None:
    rows = _rows(
        built,
        "SELECT npd_wellbore_code, depth_md, GR, ROP, PHIF, SW, KLOGH, COAL_FLAG FROM {t} "
        "WHERE source_wellbore = '15/9-F-11' ORDER BY depth_md",
    )
    # 200.2 m holds only sentinels, so it is dropped.
    assert rows == [
        (7078, 200.0, 30.0, 12.0, None, None, None, None),
        (7078, 200.1, 31.0, None, None, None, None, None),
    ]


def test_the_top_hole_section_and_the_technical_sidetrack_are_not_merged_where_they_overlap(
    built: Path,
) -> None:
    rows = _rows(
        built,
        "SELECT source_wellbore, depth_md, GR FROM {t} "
        "WHERE npd_wellbore_code = 7078 AND depth_md < 1000 ORDER BY ALL",
    )
    assert rows == [
        ("15/9-F-11", 200.0, 30.0),
        ("15/9-F-11", 200.1, 31.0),
        ("15/9-F-11 T2", 200.0, 40.0),
        ("15/9-F-11 T2", 200.1, 41.0),
        ("15/9-F-11 T2", 200.2, 42.0),
    ]


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
    assert set(curves) == {"GR", "RHOB", "ROP", "VSH", "PHIF", "COAL_FLAG", "SW", "KLOGH"}
    assert set(curves.values()) == {"DOUBLE"}


def test_no_sentinel_remains(built: Path) -> None:
    curves = ["GR", "RHOB", "ROP", "VSH", "PHIF", "COAL_FLAG", "SW", "KLOGH"]
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
    assert _rows(out / TABLE, "SELECT count(*) FROM {t}") == [(42,)]


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


def test_an_unrecognised_unit_spelling_stops_the_build(raw: Path, out: Path) -> None:
    write_las(
        pair_paths(raw, "15_9-F-1 A")[0],
        [2000.0, 2000.1],
        {"GR": ("furlongs", [80.0, 81.0])},
    )
    with pytest.raises(
        UnitSpellingError,
        match=r"15_9-F-1 A/05\.PETROPHYSICAL INTERPRETATION/WLC_PETRO_COMPUTED_INPUT_1\.LAS"
        r".*GR.*'furlongs'",
    ):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert not (out / TABLE).exists()


def test_an_output_file_beside_the_input_only_top_hole_section_stops_the_build(
    raw: Path, out: Path
) -> None:
    write_las(pair_paths(raw, TOP_HOLE[0])[1], [200.0], {"PHIF": ("v/v", [0.1])})
    with pytest.raises(SourceFileError, match=r"15/9-F-11 is mapped as input-only"):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert not (out / TABLE).exists()


def test_a_blank_unit_spelling_stops_the_build(raw: Path, out: Path) -> None:
    # A blank unit says nothing about the values; only a reviewed entry in the
    # unit table, for one mnemonic, could accept it.
    write_las(pair_paths(raw, "15_9-F-1 A")[0], [2000.0], {"GR": ("", [80.0])})
    with pytest.raises(UnitSpellingError, match=r"GR.*spelling ''"):
        volve_logs.run(raw_dir=raw, output_dir=out)


def test_a_spelling_of_another_unit_than_the_columns_stops_the_build(
    raw: Path, out: Path
) -> None:
    # g/cm3 is a known spelling, but of a density, and VSH is a fraction.
    write_las(pair_paths(raw, "15_9-F-1 A")[1], [2000.1], {"VSH": ("g/cm3", [0.4])})
    with pytest.raises(
        UnitMismatchError,
        match=r"15_9-F-1 A/.*WLC_PETRO_COMPUTED_OUTPUT_1\.LAS.*VSH.*'g/cm3'.*'g/cm³'.*'v/v'",
    ):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert not (out / TABLE).exists()


def test_a_spelling_known_for_one_mnemonic_only_stops_the_build_on_another(
    raw: Path, out: Path
) -> None:
    # UNKNOWN is accepted for RD, whose values show ohm·m, never in general.
    write_las(pair_paths(raw, "15_9-F-1 A")[0], [2000.0], {"GR": ("UNKNOWN", [80.0])})
    with pytest.raises(UnitSpellingError, match=r"GR.*'UNKNOWN'"):
        volve_logs.run(raw_dir=raw, output_dir=out)


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


# --- DLIS pairs -------------------------------------------------------------


def test_a_dlis_pair_joins_input_and_interpreted_curves_at_depths_in_metres(
    built: Path,
) -> None:
    # 15/9-F-10's index is in tenths of an inch: 1909500 is 4850.13 m. Its
    # output pads the well from 0 m with all-NULL samples, which are dropped;
    # RHOB is in both files and equal.
    rows = _rows(
        built,
        "SELECT npd_wellbore_code, depth_md, GR, RHOB, PHIF FROM {t} "
        "WHERE source_wellbore = '15/9-F-10' ORDER BY depth_md",
    )
    assert rows == [
        (6099, 4850.13, 80.5, 2.31, 0.21),
        (6099, 4850.2824, 81.5, 2.32, 0.22),
        (6099, 4850.4348, 82.5, None, 0.23),
    ]


def test_a_dlis_depth_index_in_millimetres_is_converted_to_metres(built: Path) -> None:
    rows = _rows(
        built,
        "SELECT depth_md, GR, SW FROM {t} WHERE source_wellbore = '15/9-F-15 B' ORDER BY depth_md",
    )
    assert rows == [(3500.0, 60.0, None), (3500.152, 61.0, 0.7)]


def test_padded_all_null_samples_are_dropped_and_not_counted(built: Path) -> None:
    # 15/9-F-15's input starts at 0 m with two all-NULL samples; 1000000
    # tenths of an inch is 2540 m. The build passing means the row-count check
    # compared against the one non-empty sample.
    rows = _rows(
        built, "SELECT depth_md, GR, SW FROM {t} WHERE source_wellbore = '15/9-F-15'"
    )
    assert rows == [(2540.0, 70.0, 0.8)]


def test_no_row_has_every_curve_null_for_any_source(built: Path) -> None:
    curves = [
        name
        for name, *_ in _rows(built, "SELECT column_name FROM (DESCRIBE SELECT * FROM {t})")[3:]
    ]
    empty = _rows(
        built,
        "SELECT source_wellbore, depth_md FROM {t} WHERE "
        + " AND ".join(f"{c} IS NULL" for c in curves),
    )
    assert empty == []


def test_a_shared_mnemonic_that_disagrees_in_a_dlis_pair_stops_the_build(
    raw: Path, out: Path
) -> None:
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-10")[1],
        [1909500, 1909560],
        {"RHOB": ("G/C3", [2.31, 2.35])},
    )
    with pytest.raises(CurveDisagreementError, match=r"15/9-F-10\b.*RHOB.*4850\.2824"):
        volve_logs.run(raw_dir=raw, output_dir=out)
    assert not (out / TABLE).exists()


def test_an_unrecognised_unit_spelling_in_a_dlis_file_stops_the_build(
    raw: Path, out: Path
) -> None:
    write_dlis(dlis_pair_paths(raw, "15_9-F-4")[0], [1000000], {"GR": ("furlongs", [80.0])})
    with pytest.raises(
        UnitSpellingError, match=r"15_9-F-4/.*WLC_PETRO_COMPUTED_INPUT_1\.DLIS.*GR.*'furlongs'"
    ):
        volve_logs.run(raw_dir=raw, output_dir=out)


def test_a_dlis_depth_index_in_another_unit_stops_the_build(raw: Path, out: Path) -> None:
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-4")[0], [1000], {"GR": ("API", [80.0])}, index_unit="ft"
    )
    with pytest.raises(SourceFileError, match=r"15_9-F-4/.*depth index is in 'ft'"):
        volve_logs.run(raw_dir=raw, output_dir=out)


def test_a_dlis_file_with_two_frames_stops_the_build(raw: Path, out: Path) -> None:
    # Every Volve interpretation file holds one frame; a second would need a
    # reviewed choice of which to read.
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-5")[1], [1000060], {"SW": ("V/V", [0.9])}, frames=2
    )
    with pytest.raises(SourceFileError, match=r"15_9-F-5/.*2 frame\(s\)"):
        volve_logs.run(raw_dir=raw, output_dir=out)
