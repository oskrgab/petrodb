"""Pre-publish checks on the written Curve catalog, ``log_curves.parquet``.

They read the written Parquet files, the catalog and the log tables it
describes, so they check what would be published. Any failure raises
``PrePublishCheckError`` and stops the build:

- the key ``(table_name, source_wellbore, mnemonic)`` is unique;
- every ``npd_wellbore_code`` exists in ``wells``;
- every row names a log table the build wrote;
- the catalog agrees with each table: every Curve with data for a
  ``source_wellbore`` has one row, no row names a Curve without data, and
  each row's ``npd_wellbore_code``, depth range and sample count match the
  table.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.export.volve_logs.validator import (
    PrePublishCheckError,
    check_unique_key,
    check_wellbores_in_wells,
)
from scripts.transform.volve_logs.curve_catalog import curve_columns, curve_samples
from scripts.transform.volve_logs.sql import path_literal

# How many disagreements an error lists before it stops counting them out.
MAX_LISTED = 5


def check(catalog: Path, tables: dict[str, Path], wells: Path) -> None:
    """Raise ``PrePublishCheckError`` on the first check ``catalog`` fails.

    ``tables`` maps each log table's name to its written Parquet file.
    """
    with duckdb.connect() as con:
        con.execute(f"CREATE VIEW catalog AS SELECT * FROM read_parquet({path_literal(catalog)})")
        con.execute(f"CREATE VIEW wells AS SELECT * FROM read_parquet({path_literal(wells)})")
        check_unique_key(
            con, "catalog", ("table_name", "source_wellbore", "mnemonic"), "Curve catalog key",
            lambda *key: ", ".join(key),
        )  # fmt: skip
        check_wellbores_in_wells(con, "catalog", "Curve catalog ")
        _check_tables_are_known(con, set(tables))
        for name, parquet in sorted(tables.items()):
            _check_agrees_with_table(con, name, parquet)


def _check_tables_are_known(con: duckdb.DuckDBPyConnection, tables: set[str]) -> None:
    named = {name for (name,) in con.execute("SELECT DISTINCT table_name FROM catalog").fetchall()}
    unknown = sorted(named - tables)
    if unknown:
        raise PrePublishCheckError(
            f"Curve catalog names a table the build did not write: {', '.join(unknown)}"
        )


def _check_agrees_with_table(con: duckdb.DuckDBPyConnection, name: str, parquet: Path) -> None:
    table = f"read_parquet({path_literal(parquet)})"
    samples = curve_samples(table, curve_columns(con, table))
    differences = con.execute(
        f"""
        SELECT coalesce(t.source_wellbore, c.source_wellbore) AS source_wellbore,
               coalesce(t.mnemonic, c.mnemonic) AS mnemonic,
               t.npd_wellbore_code, t.first_depth_md, t.last_depth_md, t.sample_count,
               c.npd_wellbore_code, c.first_depth_md, c.last_depth_md, c.sample_count
        FROM ({samples}) t
        FULL OUTER JOIN (SELECT * FROM catalog WHERE table_name = $name) c
            ON t.source_wellbore = c.source_wellbore AND t.mnemonic = c.mnemonic
        WHERE (t.npd_wellbore_code, t.first_depth_md, t.last_depth_md, t.sample_count)
              IS DISTINCT FROM
              (c.npd_wellbore_code, c.first_depth_md, c.last_depth_md, c.sample_count)
        ORDER BY 1, 2
        """,
        {"name": name},
    ).fetchall()
    if not differences:
        return
    described = []
    for source, mnemonic, *row in differences[:MAX_LISTED]:
        in_table, in_catalog = tuple(row[:4]), tuple(row[4:])
        if in_catalog[0] is None:
            described.append(f"{source} {mnemonic}: has data, but no catalog row")
        elif in_table[0] is None:
            described.append(f"{source} {mnemonic}: catalog row, but no data in the table")
        else:
            described.append(
                f"{source} {mnemonic}: table has (npd_wellbore_code, first, last, count) "
                f"{in_table}, catalog has {in_catalog}"
            )
    more = len(differences) - MAX_LISTED
    raise PrePublishCheckError(
        f"Curve catalog disagrees with {name}: "
        + "; ".join(described)
        + (f"; and {more} more" if more > 0 else "")
    )
