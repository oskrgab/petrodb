"""Pre-publish validation hook for the Argentina export.

Invoked unconditionally before parquet writes. Currently enforces one
of the six PRD invariants — every non-NULL `geom` in `wells` must parse
as valid WKB. Later issues add PK uniqueness, FK integrity, date
completeness, partition counts, and the 50 MB soft-warn.

Failure raises and aborts the export. Parquets are never written on a
failed validation.
"""

import duckdb


def validate(con: duckdb.DuckDBPyConnection) -> None:
    _validate_wkb_parseable(con)


def _validate_wkb_parseable(con: duckdb.DuckDBPyConnection) -> None:
    """Every non-NULL `geom` in `wells` must parse as WKB.

    DuckDB's spatial extension raises on bad input, which is exactly the
    abort behavior we want — we materialize the parse over every row
    and let any failure surface as an exception.
    """
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    # COUNT(expr) forces evaluation of ST_GeomFromWKB on every non-NULL
    # row; a wrapping COUNT(*) would let the optimizer elide the parse.
    con.execute(
        """
        SELECT COUNT(ST_GeomFromWKB(geom))
        FROM wells
        WHERE geom IS NOT NULL
        """
    ).fetchone()
