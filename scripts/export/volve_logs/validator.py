"""Pre-publish checks on the written ``petrophysical_interpretation.parquet``.

They read the Parquet file itself, so they check what would be published. Any
failure raises ``PrePublishCheckError`` and stops the build:

- the key ``(source_wellbore, depth_md)`` is unique;
- every ``npd_wellbore_code`` exists in ``wells``;
- ``depth_md`` strictly increases, in file order, within each ``source_wellbore``;
- each ``source_wellbore`` has as many rows as its source has non-empty depth samples
  (where a Curve other than a flag has a value);
- no sentinel value ``-999.25`` remains in a Curve column;
- the file is a single row group;
- the columns are in the order ``layout`` declares.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import duckdb

from scripts.export.volve_logs import layout
from scripts.transform.volve_logs.curve_catalog import curve_columns
from scripts.transform.volve_logs.las_reader import SENTINEL
from scripts.transform.volve_logs.sql import identifier, path_literal


# The written file's own columns, without the row number the checks add.
WRITTEN_COLUMNS = "(SELECT * EXCLUDE (file_row_number) FROM written)"


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
        check_unique_key(
            con, "written", ("source_wellbore", "depth_md"), "key",
            lambda source, depth: f"{source} at {depth} m",
        )  # fmt: skip
        check_wellbores_in_wells(con, "written", "")
        _check_depth_increases(con)
        _check_row_counts(con, expected_rows)
        _check_no_sentinel(con)
        _check_one_row_group(con, parquet)
        _check_column_order(con)


def check_unique_key(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    key: tuple[str, ...],
    name: str,
    describe: Callable[..., str],
) -> None:
    """Raise if two rows of ``relation`` share ``key``; ``describe`` words the
    duplicated key values for the error, which calls the key ``name``."""
    columns = ", ".join(key)
    duplicate = con.execute(
        f"SELECT {columns}, count(*) FROM {relation} "
        "GROUP BY ALL HAVING count(*) > 1 ORDER BY ALL LIMIT 1"
    ).fetchone()
    if duplicate:
        *values, n = duplicate
        raise PrePublishCheckError(
            f"duplicate {name} ({columns}): {describe(*values)} appears {n} times"
        )


def check_wellbores_in_wells(con: duckdb.DuckDBPyConnection, relation: str, label: str) -> None:
    """Raise if an ``npd_wellbore_code`` of ``relation`` is not in the ``wells`` view;
    ``label`` names the relation at the start of the error."""
    missing = con.execute(
        f"SELECT DISTINCT t.npd_wellbore_code, t.source_wellbore FROM {relation} t "
        "ANTI JOIN wells w USING (npd_wellbore_code) ORDER BY ALL"
    ).fetchall()
    if missing:
        listed = ", ".join(f"{code} ({source})" for code, source in missing)
        raise PrePublishCheckError(f"{label}npd_wellbore_code missing from wells: {listed}")


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
    for name in curve_columns(con, WRITTEN_COLUMNS):
        hit = con.execute(
            f"SELECT source_wellbore, depth_md FROM written "
            f"WHERE {identifier(name)} = {SENTINEL} ORDER BY ALL LIMIT 1"
        ).fetchone()
        if hit:
            raise PrePublishCheckError(
                f"sentinel {SENTINEL} left in Curve {name}: {hit[0]} at {hit[1]} m"
            )


def _check_one_row_group(con: duckdb.DuckDBPyConnection, parquet: Path) -> None:
    (row_groups,) = con.execute(
        f"SELECT num_row_groups FROM parquet_file_metadata({path_literal(parquet)})"
    ).fetchone()
    if row_groups != 1:
        raise PrePublishCheckError(f"the file has {row_groups} row groups, not one")


def _check_column_order(con: duckdb.DuckDBPyConnection) -> None:
    actual = [name for name, *_ in con.execute(f"DESCRIBE {WRITTEN_COLUMNS}").fetchall()]
    declared = layout.column_order(con, WRITTEN_COLUMNS)
    if actual != declared:
        raise PrePublishCheckError(
            f"column order is {', '.join(actual)}; declared {', '.join(declared)}"
        )
