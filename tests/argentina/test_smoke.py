"""End-to-end smoke test for the Argentina pipeline.

Runs the transform and export orchestrators against the fixture CSVs
(~3 wells × 2 years) and asserts that a placeholder wells.parquet is
emitted with the expected row count.
"""

from pathlib import Path

import duckdb
import pytest

from scripts.export.argentina import orchestrator as export_orch
from scripts.export.argentina import validator
from scripts.transform.argentina import orchestrator as transform_orch

FIXTURES = Path(__file__).parent.parent / "fixtures" / "argentina"


def test_pipeline_emits_wells_parquet(tmp_path: Path) -> None:
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
    assert row_count == 3, f"expected 3 wells in fixture output, got {row_count}"


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
