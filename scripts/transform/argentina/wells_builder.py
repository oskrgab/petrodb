"""Build the placeholder wells table from staged sources.

This slice emits idpozo + sigla only — the real spine (capitulo-iv +
listado LEFT JOIN, 113 orphans, geometry, etc.) is deferred to a later
issue. The shape exists so the export wiring can be exercised end-to-end.
"""

import duckdb


def build(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE wells AS
        SELECT idpozo, sigla
        FROM stg_capitulo_iv
        """
    )
