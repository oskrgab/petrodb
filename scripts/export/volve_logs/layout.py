"""The physical layout of ``petrophysical_interpretation.parquet`` (ADR-0012).

A browser log viewer reads the table fastest as one file with a single row
group, rows sorted by the key columns, the key columns first and then the
Curves the most Wellbores carry. The writer lays the file out with
``column_order``; the pre-publish checks hold the written file to it.

A Wellbore carries a Curve when the Curve has at least one value (not NULL)
in a row of that Wellbore; rows of a Technical sidetrack count for its
Wellbore, since they share its ``npd_wellbore_code``. Curves carried by as many Wellbores are ordered by
mnemonic, so the order is deterministic.
"""

from __future__ import annotations

import duckdb

from scripts.transform.volve_logs.curve_catalog import curve_columns
from scripts.transform.volve_logs.interpretation_builder import KEY_COLUMNS
from scripts.transform.volve_logs.sql import identifier


def column_order(con: duckdb.DuckDBPyConnection, relation: str) -> list[str]:
    """The declared column order for ``relation``: the keys, then its Curves."""
    curves = curve_columns(con, relation)
    if not curves:
        return list(KEY_COLUMNS)
    carriers = con.execute(
        "SELECT "
        + ", ".join(
            f"count(DISTINCT npd_wellbore_code) FILTER (WHERE {identifier(c)} IS NOT NULL)"
            for c in curves
        )
        + f" FROM {relation}"
    ).fetchone()
    ranked = sorted(zip(curves, carriers), key=lambda curve: (-curve[1], curve[0]))
    return [*KEY_COLUMNS, *(name for name, _ in ranked)]
