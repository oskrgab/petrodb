"""Write ``petrophysical_interpretation.parquet`` and its Curve catalog with DuckDB, and publish them only once checked.

The table is laid out as ``layout`` declares: one row group, rows sorted by
the key columns, the key columns first and then the Curves the most Wellbores
carry. Each file is written beside its final name. The table is checked by
``validator``, the catalog, ``log_curves.parquet``, by ``catalog_check``
against the written table, and both against the committed ``schema.json`` by
``schema_check``. Both are moved into place only when every check passes. A
failed build leaves no new file and keeps previously built ones untouched.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.export.volve_logs import catalog_check, layout, schema_check, validator
from scripts.transform.volve_logs import curve_catalog
from scripts.transform.volve_logs.interpretation_builder import KEY_COLUMNS, TABLE
from scripts.transform.volve_logs.sql import identifier, path_literal

FILENAME = f"{TABLE}.parquet"
CATALOG_FILENAME = f"{curve_catalog.CATALOG}.parquet"


def write(
    con: duckdb.DuckDBPyConnection,
    output_dir: Path,
    wells: Path,
    schema: Path,
    expected_rows: dict[str, int],
) -> Path:
    """Write the table in its declared layout and its catalog, check both, and return the table's path."""
    output_dir = Path(output_dir)
    final = output_dir / FILENAME
    pending = output_dir / f".{FILENAME}.pending"
    catalog_final = output_dir / CATALOG_FILENAME
    catalog_pending = output_dir / f".{CATALOG_FILENAME}.pending"
    columns = ", ".join(identifier(c) for c in layout.column_order(con, TABLE))
    order = ", ".join(KEY_COLUMNS)
    catalog_order = ", ".join(curve_catalog.SORT_COLUMNS)
    (rows,) = con.execute(f"SELECT count(*) FROM {TABLE}").fetchone()
    try:
        # A row group holds up to ROW_GROUP_SIZE rows, so every row fits in one.
        con.execute(
            f"COPY (SELECT {columns} FROM {TABLE} ORDER BY {order}) "
            f"TO {path_literal(pending)} (FORMAT parquet, ROW_GROUP_SIZE {max(rows, 1)})"
        )
        con.execute(
            f"COPY (SELECT * FROM {curve_catalog.CATALOG} ORDER BY {catalog_order}) "
            f"TO {path_literal(catalog_pending)} (FORMAT parquet)"
        )
        validator.check(pending, wells, expected_rows)
        schema_check.check(pending, schema)
        schema_check.check(catalog_pending, schema, curve_catalog.CATALOG)
        catalog_check.check(catalog_pending, {TABLE: pending}, wells)
        pending.replace(final)
        catalog_pending.replace(catalog_final)
    finally:
        pending.unlink(missing_ok=True)
        catalog_pending.unlink(missing_ok=True)
    return final
