"""Argentina export-phase orchestrator.

Validates the intermediate DB unconditionally, then writes the published
Parquets. For this slice only `wells.parquet` is emitted.
"""

from pathlib import Path

import duckdb

from scripts.export.argentina import parquet_writer, validator


def run(db_path: Path, output_dir: Path) -> None:
    db_path = Path(db_path)
    output_dir = Path(output_dir)

    with duckdb.connect(str(db_path), read_only=True) as con:
        validator.validate(con)
        parquet_writer.write_wells(con, output_dir)
