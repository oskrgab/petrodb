"""Pre-publish checks on the written ``petrophysical_interpretation.parquet``.

They read the Parquet file itself, so they check what would be published. Any
failure raises ``PrePublishCheckError`` and stops the build:

- the key ``(source_wellbore, depth_md)`` is unique;
- every ``npd_wellbore_code`` exists in ``wells``;
- ``depth_md`` strictly increases, in file order, within each ``source_wellbore``;
- each ``source_wellbore`` has as many rows as its source has non-empty depth samples;
- no sentinel value ``-999.25`` remains in a Curve column.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.transform.volve_logs.interpretation_builder import KEY_COLUMNS
from scripts.transform.volve_logs.las_reader import SENTINEL
from scripts.transform.volve_logs.sql import identifier, path_literal


class PrePublishCheckError(Exception):
    """The written table breaks a pre-publish check."""


def check(parquet: Path, wells: Path, expected_rows: dict[str, int]) -> None:
    """Raise ``PrePublishCheckError`` on the first check ``parquet`` fails."""
    with duckdb.connect() as con:
        con.execute(
            "CREATE VIEW written AS SELECT * FROM "
            f"read_parquet({path_literal(parquet)}, file_row_number = true)"
        )
        con.execute(f"CREATE VIEW wells AS SELECT * FROM read_parquet({path_literal(wells)})")
        _check_unique_key(con)
        _check_wellbores_in_wells(con)
        _check_depth_increases(con)
        _check_row_counts(con, expected_rows)
        _check_no_sentinel(con)


def _check_unique_key(con: duckdb.DuckDBPyConnection) -> None:
    duplicate = con.execute(
        "SELECT source_wellbore, depth_md, count(*) FROM written "
        "GROUP BY ALL HAVING count(*) > 1 ORDER BY ALL LIMIT 1"
    ).fetchone()
    if duplicate:
        source, depth, n = duplicate
        raise PrePublishCheckError(
            f"duplicate key (source_wellbore, depth_md): {source} at {depth} m appears {n} times"
        )


def _check_wellbores_in_wells(
    con: duckdb.DuckDBPyConnection
) -> None:
    missing = con.execute(
        "SELECT DISTINCT t.npd_wellbore_code, t.source_wellbore FROM written t "
        "ANTI JOIN wells w USING (npd_wellbore_code) ORDER BY ALL"
    ).fetchall()
    if missing:
        listed = ", ".join(f"{code} ({source})" for code, source in missing)
        raise PrePublishCheckError(f"npd_wellbore_code missing from wells: {listed}")


def _check_depth_increases(con: duckdb.DuckDBPyConnection) -> None:
    bad = con.execute(
        """
        SELECT source_wellbore, depth_md, previous FROM (
            SELECT source_wellbore, depth_md,
                   lag(depth_md) OVER (
                       PARTITION BY source_wellbore ORDER BY file_row_number
                   ) AS previous
            FROM written
        )
        WHERE depth_md <= previous
        ORDER BY ALL LIMIT 1
        """
    ).fetchone()
    if bad:
        source, depth, previous = bad
        raise PrePublishCheckError(
            f"depth_md does not strictly increase for {source}: {depth} m follows {previous} m"
        )


def _check_row_counts(
    con: duckdb.DuckDBPyConnection, expected_rows: dict[str, int]
) -> None:
    written = dict(
        con.execute("SELECT source_wellbore, count(*) FROM written GROUP BY ALL").fetchall()
    )
    differences = [
        f"{source}: {written.get(source, 0)} rows, source has {expected_rows.get(source, 0)}"
        for source in sorted(set(written) | set(expected_rows))
        if written.get(source, 0) != expected_rows.get(source, 0)
    ]
    if differences:
        raise PrePublishCheckError("row count differs from the source: " + "; ".join(differences))


def _check_no_sentinel(con: duckdb.DuckDBPyConnection) -> None:
    curves = [
        name
        for name, *_ in con.execute("DESCRIBE SELECT * EXCLUDE (file_row_number) FROM written").fetchall()
        if name not in KEY_COLUMNS
    ]
    for name in curves:
        hit = con.execute(
            f"SELECT source_wellbore, depth_md FROM written "
            f"WHERE {identifier(name)} = {SENTINEL} ORDER BY ALL LIMIT 1"
        ).fetchone()
        if hit:
            raise PrePublishCheckError(
                f"sentinel {SENTINEL} left in Curve {name}: {hit[0]} at {hit[1]} m"
            )
