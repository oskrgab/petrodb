"""Write ``petrophysical_interpretation.parquet`` with DuckDB, and publish it only once checked.

The file is written beside its final name, checked by ``validator``, and moved
into place only when every check passes; a failed build leaves no table and
keeps a previously built one untouched.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.export.volve_logs import validator
from scripts.transform.volve_logs.interpretation_builder import KEY_COLUMNS, TABLE

FILENAME = f"{TABLE}.parquet"


def write(
    con: duckdb.DuckDBPyConnection,
    output_dir: Path,
    wells: Path,
    expected_rows: dict[str, int],
) -> Path:
    """Write the table sorted by its key columns, check it, and return its path."""
    output_dir = Path(output_dir)
    final = output_dir / FILENAME
    pending = output_dir / f".{FILENAME}.pending"
    order = ", ".join(KEY_COLUMNS)
    try:
        con.execute(
            f"COPY (SELECT * FROM {TABLE} ORDER BY {order}) "
            f"TO {validator.sql_path(pending)} (FORMAT parquet)"
        )
        validator.check(pending, wells, expected_rows)
        pending.replace(final)
    finally:
        pending.unlink(missing_ok=True)
    return final
