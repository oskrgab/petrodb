"""Argentina transform-phase orchestrator.

Stages source CSVs into the DuckDB intermediate, then builds the
destination tables. For this slice only `wells` is built; later issues
add `well_operator_history`, `well_events`, and `monthly_production`.
"""

from pathlib import Path

import duckdb

from scripts.transform.argentina import csv_stager, wells_builder


def run(db_path: Path, csv_dir: Path) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        csv_stager.stage(con, csv_dir)
        wells_builder.build(con)
