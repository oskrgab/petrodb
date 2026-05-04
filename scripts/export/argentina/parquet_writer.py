"""Write Argentina destination tables to Parquet via pure DuckDB SQL.

For this slice only `wells.parquet` is emitted (single file). Later
issues add `well_operator_history.parquet`, `well_events.parquet`, and
the hive-partitioned `monthly_production/anio=YYYY/data.parquet` tree.
"""

from pathlib import Path

import duckdb


def write_wells(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "wells.parquet"
    con.execute(f"COPY (SELECT * FROM wells) TO '{target}' (FORMAT PARQUET)")
