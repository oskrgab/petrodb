"""Write ``petrophysical_interpretation.parquet`` and its Curve catalog with DuckDB, and publish them only once checked.

Each file is written beside its final name. The table is checked by
``validator`` and the catalog, ``log_curves.parquet``, by ``catalog_check``
against the written table; both are moved into place only when every check
passes. A failed build leaves no new file and keeps previously built ones
untouched.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.export.volve_logs import catalog_check, validator
from scripts.transform.volve_logs import curve_catalog
from scripts.transform.volve_logs.interpretation_builder import KEY_COLUMNS, TABLE
from scripts.transform.volve_logs.sql import path_literal

FILENAME = f"{TABLE}.parquet"
CATALOG_FILENAME = f"{curve_catalog.CATALOG}.parquet"


def write(
    con: duckdb.DuckDBPyConnection,
    output_dir: Path,
    wells: Path,
    expected_rows: dict[str, int],
) -> Path:
    """Write the table sorted by its key columns and its catalog, check both, and return the table's path."""
    output_dir = Path(output_dir)
    final = output_dir / FILENAME
    pending = output_dir / f".{FILENAME}.pending"
    catalog_final = output_dir / CATALOG_FILENAME
    catalog_pending = output_dir / f".{CATALOG_FILENAME}.pending"
    order = ", ".join(KEY_COLUMNS)
    catalog_order = ", ".join(curve_catalog.SORT_COLUMNS)
    try:
        con.execute(
            f"COPY (SELECT * FROM {TABLE} ORDER BY {order}) "
            f"TO {path_literal(pending)} (FORMAT parquet)"
        )
        con.execute(
            f"COPY (SELECT * FROM {curve_catalog.CATALOG} ORDER BY {catalog_order}) "
            f"TO {path_literal(catalog_pending)} (FORMAT parquet)"
        )
        validator.check(pending, wells, expected_rows)
        catalog_check.check(catalog_pending, {TABLE: pending}, wells)
        pending.replace(final)
        catalog_pending.replace(catalog_final)
    finally:
        pending.unlink(missing_ok=True)
        catalog_pending.unlink(missing_ok=True)
    return final
