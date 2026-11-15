"""Build the Curve catalog, ``log_curves``: one row per log table, ``source_wellbore`` and Curve.

A reader fetches it first to learn which Curves exist, for which Wellbore or
Technical sidetrack, over which depths, and where each came from. Two steps:

- while a log table is built, ``record`` notes where each Curve of a
  ``source_wellbore`` came from: the file (as a path within the Raw repo),
  whether it is an Input curve or an Interpreted curve, and the file's unit
  spelling. The first file that carries a mnemonic names it, so a Curve in
  both files of a pair is an Input curve and names the input file. A single
  interpretation file holds both kinds of Curve: ``split_by_kind`` divides it
  by the committed list ``SINGLE_FILE_CURVE_KINDS``;
- ``build`` then reads each Curve's first and last depth with data and its
  count of non-null samples from the built table itself. A Curve entirely
  NULL for a ``source_wellbore`` has no row.

The catalog carries no free-text description copied from a source header.
"""

from __future__ import annotations

from pathlib import PurePath

import duckdb
import pyarrow as pa

from scripts.transform.volve_logs.sql import identifier
from scripts.transform.volve_logs.units import CURVE_UNITS, UNIT_METADATA_KEY

CATALOG = "log_curves"
# The row key every log table starts with; every other column is a Curve.
TABLE_KEY_COLUMNS = ("npd_wellbore_code", "source_wellbore", "depth_md")
SORT_COLUMNS = ("table_name", "npd_wellbore_code", "source_wellbore", "mnemonic")
INPUT = "input"
INTERPRETED = "interpreted"

_SOURCES = "curve_sources"

# What each Curve of a single interpretation file is (the 15/9-19
# wellbores). A Curve the interpretation took as measured is an Input curve,
# as in the input files of a pair: the bit size and the sonic. Everything
# else it computed or set, its parameters included (matrix and fluid density,
# formation-water resistivity, temperature, the gamma-ray end points, the
# saturation and cementation exponents), is an Interpreted curve.
_SINGLE_FILE_INPUT_CURVES = ("BS", "DT")
_SINGLE_FILE_INTERPRETED_CURVES = (
    "BVW", "BWV", "CARB_FLAG", "COAL_FLAG", "DELTA", "GRMAX", "GRMIN", "J",
    "KLHC_INT", "KLOGH", "KLOGV", "M", "N", "PERF_FLAG", "PHIF", "PORD",
    "RHOFL", "RHOMA", "RW", "SAND_FLAG", "SW", "SWIRR", "TEMP", "VSH",
)  # fmt: skip
SINGLE_FILE_CURVE_KINDS: dict[str, str] = {
    **dict.fromkeys(_SINGLE_FILE_INPUT_CURVES, INPUT),
    **dict.fromkeys(_SINGLE_FILE_INTERPRETED_CURVES, INTERPRETED),
}


class UnclassifiedCurveError(Exception):
    """A single interpretation file carries a Curve the committed list does not classify."""


def split_by_kind(path: PurePath, table: pa.Table) -> tuple[pa.Table, pa.Table]:
    """``table``, read from a single interpretation file at ``path``, as its
    Input curves and its Interpreted curves, each keeping the depth column.

    Fails on a Curve ``SINGLE_FILE_CURVE_KINDS`` does not list.
    """
    curves = [f.name for f in table.schema if UNIT_METADATA_KEY in (f.metadata or {})]
    unclassified = [name for name in curves if name not in SINGLE_FILE_CURVE_KINDS]
    if unclassified:
        raise UnclassifiedCurveError(
            f"{path}: Curve(s) {', '.join(unclassified)} not listed as Input or "
            "Interpreted in SINGLE_FILE_CURVE_KINDS"
        )
    others = [name for name in table.column_names if name not in curves]

    def of_kind(kind: str) -> pa.Table:
        return table.select(
            others + [name for name in curves if SINGLE_FILE_CURVE_KINDS[name] == kind]
        )

    return of_kind(INPUT), of_kind(INTERPRETED)


def create(con: duckdb.DuckDBPyConnection) -> None:
    """Start an empty record of Curve sources in ``con``."""
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE {_SOURCES} ("
        "table_name VARCHAR NOT NULL, source_wellbore VARCHAR NOT NULL, "
        "mnemonic VARCHAR NOT NULL, curve_kind VARCHAR NOT NULL, unit VARCHAR NOT NULL, "
        "source_unit VARCHAR NOT NULL, source_file VARCHAR NOT NULL, "
        "PRIMARY KEY (table_name, source_wellbore, mnemonic))"
    )


def record(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    source_wellbore: str,
    files: list[tuple[str, PurePath, pa.Table]],
) -> None:
    """Note where each Curve of ``source_wellbore`` in ``table_name`` came from.

    ``files`` holds ``(curve_kind, path within the Raw repo, table read from
    it)``, in the order that decides which file names a mnemonic in several.
    Curves are the fields with a ``unit`` in their metadata.
    """
    seen: set[str] = set()
    rows = []
    for kind, path, table in files:
        for field in table.schema:
            unit = (field.metadata or {}).get(UNIT_METADATA_KEY)
            if unit is None or field.name in seen:
                continue
            seen.add(field.name)
            rows.append(
                (table_name, source_wellbore, field.name, kind, CURVE_UNITS[field.name],
                 unit.decode(), PurePath(path).as_posix())
            )  # fmt: skip
    if rows:
        con.executemany(f"INSERT INTO {_SOURCES} VALUES (?, ?, ?, ?, ?, ?, ?)", rows)


def curve_samples(relation: str, curves: list[str]) -> str:
    """SQL: per ``source_wellbore`` and Curve of ``relation``, its depth range and sample count.

    ``relation`` has ``npd_wellbore_code``, ``source_wellbore``, ``depth_md``
    and the ``curves`` columns. A Curve with no sample for a
    ``source_wellbore`` gives no row.
    """
    columns = ", ".join(identifier(c) for c in curves)
    return (
        "SELECT npd_wellbore_code, source_wellbore, mnemonic, "
        "min(depth_md) AS first_depth_md, max(depth_md) AS last_depth_md, "
        "count(*) AS sample_count FROM ("
        f"UNPIVOT (SELECT npd_wellbore_code, source_wellbore, depth_md, {columns} "
        f"FROM {relation}) ON {columns} INTO NAME mnemonic VALUE sample"
        ") GROUP BY ALL"
    )


def curve_columns(con: duckdb.DuckDBPyConnection, relation: str) -> list[str]:
    """The Curve columns of a log table: every column but the row key."""
    return [
        name
        for name, *_ in con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
        if name not in TABLE_KEY_COLUMNS
    ]


def build(con: duckdb.DuckDBPyConnection, table_name: str) -> None:
    """Create ``log_curves`` in ``con`` from the built ``table_name`` and the recorded sources."""
    curves = curve_columns(con, identifier(table_name))
    con.execute(
        f"CREATE OR REPLACE TABLE {CATALOG} ("
        "table_name VARCHAR NOT NULL, npd_wellbore_code BIGINT NOT NULL, "
        "source_wellbore VARCHAR NOT NULL, mnemonic VARCHAR NOT NULL, "
        "curve_kind VARCHAR NOT NULL, unit VARCHAR NOT NULL, source_unit VARCHAR NOT NULL, "
        "first_depth_md DOUBLE NOT NULL, last_depth_md DOUBLE NOT NULL, "
        "sample_count BIGINT NOT NULL, source_file VARCHAR NOT NULL)"
    )
    # A Curve with samples but no recorded source leaves NULLs, which the NOT
    # NULL columns refuse: the build stops instead of publishing a gap.
    con.execute(
        f"INSERT INTO {CATALOG} "
        "SELECT $table_name, c.npd_wellbore_code, c.source_wellbore, c.mnemonic, "
        "s.curve_kind, s.unit, s.source_unit, c.first_depth_md, c.last_depth_md, "
        "c.sample_count, s.source_file "
        f"FROM ({curve_samples(identifier(table_name), curves)}) c "
        f"LEFT JOIN {_SOURCES} s ON s.table_name = $table_name "
        "AND s.source_wellbore = c.source_wellbore AND s.mnemonic = c.mnemonic",
        {"table_name": table_name},
    )
