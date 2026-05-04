"""End-to-end smoke test for the Argentina pipeline.

Runs the transform and export orchestrators against the fixture CSVs
(~3 wells × 2 years) and asserts that a placeholder wells.parquet is
emitted with the expected row count.
"""

from pathlib import Path

import duckdb
import pytest

from scripts.explore.argentina import eda_plotter
from scripts.explore.argentina import orchestrator as explore_orch
from scripts.export.argentina import orchestrator as export_orch
from scripts.export.argentina import validator
from scripts.transform.argentina import orchestrator as transform_orch

FIXTURES = Path(__file__).parent.parent / "fixtures" / "argentina"


def test_pipeline_emits_wells_parquet(tmp_path: Path) -> None:
    """Fixture has 4 capitulo-iv wells (one orphan) + 2 production-only.
    All six are emitted in wells.parquet."""
    db_path = tmp_path / "argentina.duckdb"
    out_dir = tmp_path / "parquet"

    transform_orch.run(db_path=db_path, csv_dir=FIXTURES)
    export_orch.run(db_path=db_path, output_dir=out_dir)

    wells_parquet = out_dir / "wells.parquet"
    assert wells_parquet.exists(), "wells.parquet was not written"

    con = duckdb.connect()
    row_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{wells_parquet}')"
    ).fetchone()[0]
    assert row_count == 6, f"expected 6 wells in fixture output, got {row_count}"

    # Spot-check has_production: orphan 1004 false, all others true
    flags = dict(
        con.execute(
            f"SELECT idpozo, has_production "
            f"FROM read_parquet('{wells_parquet}') ORDER BY idpozo"
        ).fetchall()
    )
    assert flags == {
        1001: True,
        1002: True,
        1003: True,
        1004: False,
        1005: True,
        1006: True,
    }

    # Dropped admin/audit columns must not appear in the published parquet
    cols = {
        row[0]
        for row in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{wells_parquet}')"
        ).fetchall()
    }
    forbidden = {
        "geojson",
        "observaciones",
        "idusuario",
        "rectificado",
        "habilitado",
        "fechaingreso",
        "fecha_data",
    }
    assert not (cols & forbidden)

    # well_operator_history.parquet — fixture has 1002 transitioning
    # Z001 (2006) → APEA (2007); other producing wells have a single run.
    op_parquet = out_dir / "well_operator_history.parquet"
    assert op_parquet.exists(), "well_operator_history.parquet was not written"
    intervals_per_well = dict(
        con.execute(
            f"""
            SELECT idpozo, COUNT(*)
            FROM read_parquet('{op_parquet}')
            GROUP BY idpozo
            ORDER BY idpozo
            """
        ).fetchall()
    )
    assert intervals_per_well == {1001: 1, 1002: 2, 1003: 1, 1005: 1, 1006: 1}

    # 1002's two intervals must carry the expected idempresa codes.
    well_1002_codes = [
        row[0]
        for row in con.execute(
            f"""
            SELECT idempresa
            FROM read_parquet('{op_parquet}')
            WHERE idpozo = 1002
            ORDER BY valid_from
            """
        ).fetchall()
    ]
    assert well_1002_codes == ["Z001", "APEA"]

    # well_events.parquet — every producing well emits its initial state;
    # 1003 additionally flaps tipoestado Ee → Pt (2007-01) → Ee (2007-02),
    # so it carries three events. Orphan 1004 has no production rows and
    # therefore contributes no events.
    events_parquet = out_dir / "well_events.parquet"
    assert events_parquet.exists(), "well_events.parquet was not written"
    events_per_well = dict(
        con.execute(
            f"""
            SELECT idpozo, COUNT(*)
            FROM read_parquet('{events_parquet}')
            GROUP BY idpozo
            ORDER BY idpozo
            """
        ).fetchall()
    )
    assert events_per_well == {1001: 1, 1002: 1, 1003: 3, 1005: 1, 1006: 1}

    # 1003's three events in order — initial, flap-out, flap-back.
    well_1003_states = [
        row[0]
        for row in con.execute(
            f"""
            SELECT tipoestado
            FROM read_parquet('{events_parquet}')
            WHERE idpozo = 1003
            ORDER BY event_date
            """
        ).fetchall()
    ]
    assert well_1003_states == [
        "Extracción Efectiva",
        "Parado Transitoriamente",
        "Extracción Efectiva",
    ]

    # monthly_production — hive-partitioned by anio with a _files.json
    # manifest. Fixture wells:
    #   1001/1002/1003: 2006-01..2007-02 (gap-fill Mar-Dec 2006) → 14 rows each
    #   1005/1006:      2006-01 + 2007-01 (gap-fill Feb-Dec 2006) → 13 rows each
    #   1004 (orphan):  no production, no rows
    # Per partition: anio=2006 → 60 rows, anio=2007 → 8 rows. Total 68.
    mp_root = out_dir / "monthly_production"
    assert (mp_root / "anio=2006" / "data.parquet").exists()
    assert (mp_root / "anio=2007" / "data.parquet").exists()

    mp_glob = str(mp_root / "anio=*" / "data.parquet")
    rows_per_well = dict(
        con.execute(
            f"""
            SELECT idpozo, COUNT(*)
            FROM read_parquet('{mp_glob}', hive_partitioning = true)
            GROUP BY idpozo
            ORDER BY idpozo
            """
        ).fetchall()
    )
    assert rows_per_well == {1001: 14, 1002: 14, 1003: 14, 1005: 13, 1006: 13}

    rows_per_year = dict(
        con.execute(
            f"""
            SELECT anio, COUNT(*)
            FROM read_parquet('{mp_glob}', hive_partitioning = true)
            GROUP BY anio
            ORDER BY anio
            """
        ).fetchall()
    )
    assert rows_per_year == {2006: 60, 2007: 8}

    # Within each partition, rows must be sorted by (idpozo, fecha) so
    # that DuckDB row-group statistics support single-well pruning.
    file_rows = con.execute(
        f"""
        SELECT idpozo, fecha
        FROM read_parquet('{mp_root}/anio=2006/data.parquet')
        """
    ).fetchall()
    assert file_rows == sorted(file_rows), "anio=2006 partition must be sorted"

    # _files.json manifest lists both partitions in sorted order.
    import json

    manifest = json.loads((mp_root / "_files.json").read_text())
    assert manifest == ["anio=2006/data.parquet", "anio=2007/data.parquet"]

    # Source `anio` / `mes` must not be physically stored in the parquet —
    # `fecha` is the only time column. The hive-partition `anio` column
    # reappears via directory inference, so we read with hive_partitioning
    # disabled to inspect the file's actual schema.
    mp_cols = {
        row[0]
        for row in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet("
            f"'{mp_root}/anio=2006/data.parquet', hive_partitioning = false)"
        ).fetchall()
    }
    assert "mes" not in mp_cols
    assert "anio" not in mp_cols
    assert mp_cols == {
        "idpozo",
        "fecha",
        "prod_pet",
        "prod_gas",
        "prod_agua",
        "iny_agua",
        "iny_gas",
        "iny_co2",
        "iny_otro",
        "tef",
        "vida_util",
    }


def test_export_aborts_when_validator_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The validator hook must run unconditionally before any parquet write."""
    db_path = tmp_path / "argentina.duckdb"
    out_dir = tmp_path / "parquet"

    transform_orch.run(db_path=db_path, csv_dir=FIXTURES)

    def boom(_con: duckdb.DuckDBPyConnection) -> None:
        raise RuntimeError("validation failed")

    monkeypatch.setattr(validator, "validate", boom)

    with pytest.raises(RuntimeError, match="validation failed"):
        export_orch.run(db_path=db_path, output_dir=out_dir)

    assert not (out_dir / "wells.parquet").exists()


def test_explore_phase_writes_all_outputs(tmp_path: Path) -> None:
    """Explore orchestrator runs end-to-end against the fixture and emits
    every documented output (machine-readable Parquets, 12 PNGs, FINDINGS.md).

    The fixture is too small to reproduce the headline volatility numbers
    from CONTEXT.md — this test only exercises the wiring."""
    db_path = tmp_path / "argentina.duckdb"
    output_dir = tmp_path / "explore_out"

    explore_orch.run(db_path=db_path, csv_dir=FIXTURES, output_dir=output_dir)

    expected_tabular = (
        "volatility_report.parquet",
        "master_coverage.parquet",
        "master_field_agreement.parquet",
        "production_only_wells.parquet",
        "capitulo_iv_only_orphans.parquet",
        "gap_audit.parquet",
    )
    for name in expected_tabular:
        assert (output_dir / name).exists(), f"{name} was not written"

    for png in eda_plotter.PLOTS:
        path = output_dir / png
        assert path.exists(), f"{png} was not written"
        assert path.stat().st_size > 0, f"{png} is empty"
    assert len(eda_plotter.PLOTS) == 12

    findings = output_dir / "FINDINGS.md"
    assert findings.exists()
    body = findings.read_text()
    assert "Volatility scan" in body
    assert "Master reconciliation" in body
    assert "Gap audit" in body


def test_explore_phase_is_idempotent(tmp_path: Path) -> None:
    """Re-running the explore phase overwrites prior outputs deterministically."""
    db_path = tmp_path / "argentina.duckdb"
    output_dir = tmp_path / "explore_out"

    explore_orch.run(db_path=db_path, csv_dir=FIXTURES, output_dir=output_dir)
    first_findings = (output_dir / "FINDINGS.md").read_text()

    explore_orch.run(db_path=db_path, csv_dir=FIXTURES, output_dir=output_dir)
    second_findings = (output_dir / "FINDINGS.md").read_text()

    assert first_findings == second_findings
