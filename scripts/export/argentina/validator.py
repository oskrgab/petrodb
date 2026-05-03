"""Pre-publish validation hook for the Argentina export.

Invoked unconditionally before parquet writes. This slice is a trivial
pass-through; later issues populate the 6 invariants from the PRD
(unique (idpozo, fecha), FK integrity, date-completeness, parseable WKB,
etc.). Raise if any invariant fails — never write parquets on a failed
validation.
"""

import duckdb


def validate(con: duckdb.DuckDBPyConnection) -> None:
    return None
