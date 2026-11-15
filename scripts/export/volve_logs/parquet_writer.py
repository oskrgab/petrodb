"""Write ``petrophysical_interpretation.parquet`` with DuckDB, and publish it only once checked.

The file is laid out as ``layout`` declares: one row group, rows sorted by the
key columns, the key columns first and then the Curves the most Wellbores
carry. It is written beside its final name, checked by ``validator`` and
against the committed ``schema.json`` by ``schema_check``, and moved into
place only when every check passes; a failed build leaves no table
and keeps a previously built one untouched.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.export.volve_logs import layout, schema_check, validator
from scripts.transform.volve_logs.interpretation_builder import KEY_COLUMNS, TABLE
from scripts.transform.volve_logs.sql import identifier, path_literal

FILENAME = f"{TABLE}.parquet"


def write(
    con: duckdb.DuckDBPyConnection,
    output_dir: Path,
    wells: Path,
    schema: Path,
    expected_rows: dict[str, int],
) -> Path:
    """Write the table in its declared layout, check it, and return its path."""
    output_dir = Path(output_dir)
    final = output_dir / FILENAME
    pending = output_dir / f".{FILENAME}.pending"
    columns = ", ".join(identifier(c) for c in layout.column_order(con, TABLE))
    order = ", ".join(KEY_COLUMNS)
    (rows,) = con.execute(f"SELECT count(*) FROM {TABLE}").fetchone()
    try:
        # A row group holds up to ROW_GROUP_SIZE rows, so every row fits in one.
        con.execute(
            f"COPY (SELECT {columns} FROM {TABLE} ORDER BY {order}) "
            f"TO {path_literal(pending)} (FORMAT parquet, ROW_GROUP_SIZE {max(rows, 1)})"
        )
        validator.check(pending, wells, expected_rows)
        schema_check.check(pending, schema)
        pending.replace(final)
    finally:
        pending.unlink(missing_ok=True)
    return final
