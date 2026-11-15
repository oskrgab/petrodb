"""Join each source's LAS or DLIS files into the ``petrophysical_interpretation`` table.

The input and output files of a pair share a depth grid, so they are joined on
``depth_md`` (rounded to four decimals): Input curves and Interpreted curves
side by side, one row per depth sample, at the source depths. A mnemonic in
both files becomes one column, and the build fails if the two files disagree
on it at any depth they share. A source with an input file only has every
Interpreted curve NULL.

A row is kept only where a Curve other than a flag (``FLAG_CURVES``) has a
value. Rows where every other Curve is NULL are padding and are dropped: some
files pad the whole Wellbore with samples whose only value is a flag, such as
15/9-F-10's output, which carries ``CARB_FLAG = 0`` from 0 m down to where its
interpretation starts. The row-count check counts source depths by the same
rule.

Every Curve column is DOUBLE and named with the source mnemonic verbatim; a
mnemonic ``volve_descriptions`` does not list fails the build, so every
published column is documented. Each file's unit spellings must mean the unit
documented for the column (``units``); values are not converted. The published
column order is the writer's (``scripts.export.volve_logs.layout``).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from scripts.export.volve_descriptions import COLUMN_DESCRIPTIONS
from scripts.transform.volve_logs import curve_catalog, units
from scripts.transform.volve_logs.dlis_reader import read_dlis
from scripts.transform.volve_logs.las_reader import DEPTH_COLUMN, read_las
from scripts.transform.volve_logs.sources import DLIS, LAS, SOURCES, LogSource, SourceFileError
from scripts.transform.volve_logs.sql import identifier as _q

TABLE = "petrophysical_interpretation"
KEY_COLUMNS = ("npd_wellbore_code", "source_wellbore", DEPTH_COLUMN)
DEPTH_DECIMALS = 4
# Flags hold 0 or 1 wherever a file samples, padding included, so a value in
# one of them alone does not make a row.
FLAG_CURVES = frozenset({"BADDATA_FLAG", "CARB_FLAG", "COAL_FLAG", "SAND_FLAG"})
DOCUMENTED_CURVES = tuple(
    name for name in COLUMN_DESCRIPTIONS[TABLE] if name not in KEY_COLUMNS
)


READERS = {LAS: read_las, DLIS: read_dlis}


class CurveDisagreementError(Exception):
    """A mnemonic in both files of a pair holds different values at one depth."""


class UndocumentedCurveError(Exception):
    """A source mnemonic has no description, so it cannot be published."""


def _curves(table: pa.Table) -> list[str]:
    return [name for name in table.column_names if name != DEPTH_COLUMN]


def _not_flags(curves: list[str]) -> list[str]:
    """The Curves whose values make a row worth keeping: every Curve but the flags."""
    return [name for name in curves if name not in FLAG_CURVES]


def _non_empty_depths(table: pa.Table) -> set[float]:
    """Rounded depths where at least one Curve other than a flag has a value."""
    has_value = np.zeros(table.num_rows, dtype=bool)
    for name in _not_flags(_curves(table)):
        has_value |= pc.is_valid(table[name]).to_numpy(zero_copy_only=False)
    depths = np.round(table[DEPTH_COLUMN].to_numpy(), DEPTH_DECIMALS)
    return set(depths[has_value].tolist())


def _read_output(source: LogSource, raw_dir: Path) -> pa.Table:
    """The output file, or a table with no samples for a source with none.

    An output file beside an input-only source means the mapping is out of
    date, so it stops the build rather than being ignored.
    """
    path = source.output_path(raw_dir)
    if path is None:
        unexpected = source.unread_output_path(raw_dir)
        if unexpected.exists():
            raise SourceFileError(
                f"{source.source_wellbore} is mapped as input-only, "
                f"but has an output file: {unexpected}"
            )
        return pa.table({DEPTH_COLUMN: pa.array([], pa.float64())})
    return READERS[source.file_format](path)


def build(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> dict[str, int]:
    """Create ``petrophysical_interpretation`` in ``con`` from the sources under ``raw_dir``.

    Each Curve's source file is recorded for the Curve catalog
    (``curve_catalog``). Returns the number of non-empty depth samples each
    ``source_wellbore`` has
    in its source files, counted from the files themselves, for the
    pre-publish row-count check.
    """
    read = [
        (
            source,
            READERS[source.file_format](source.input_path(raw_dir)),
            _read_output(source, raw_dir),
        )
        for source in SOURCES
    ]
    present = {
        name
        for _, input_table, output_table in read
        for name in _curves(input_table) + _curves(output_table)
    }
    undocumented = sorted(present - set(DOCUMENTED_CURVES))
    if undocumented:
        raise UndocumentedCurveError(
            f"Curve(s) with no description in volve_descriptions: {', '.join(undocumented)}"
        )
    for source, input_table, output_table in read:
        units.check(source.input_path(raw_dir), input_table)
        units.check(source.output_path(raw_dir), output_table)
    curves = [name for name in DOCUMENTED_CURVES if name in present]

    con.execute(
        f"CREATE OR REPLACE TABLE {TABLE} ("
        "npd_wellbore_code BIGINT NOT NULL, source_wellbore VARCHAR NOT NULL, "
        f"{DEPTH_COLUMN} DOUBLE NOT NULL"
        + "".join(f", {_q(c)} DOUBLE" for c in curves)
        + ")"
    )
    curve_catalog.create(con)
    expected_rows = {}
    for source, input_table, output_table in read:
        _insert_source(con, source, input_table, output_table)
        _record_curve_sources(con, source, input_table, output_table)
        expected_rows[source.source_wellbore] = len(
            _non_empty_depths(input_table) | _non_empty_depths(output_table)
        )
    return expected_rows


def _record_curve_sources(
    con: duckdb.DuckDBPyConnection,
    source: LogSource,
    input_table: pa.Table,
    output_table: pa.Table,
) -> None:
    """Note each Curve's file for the Curve catalog: the input file first, so a
    mnemonic in both files is an Input curve named after the input file."""
    in_raw_repo = Path()  # an empty root gives each path within the Raw repo
    files = [(curve_catalog.INPUT, source.input_path(in_raw_repo), input_table)]
    output_path = source.output_path(in_raw_repo)
    if output_path is not None:
        files.append((curve_catalog.INTERPRETED, output_path, output_table))
    curve_catalog.record(con, TABLE, source.source_wellbore, files)


def _insert_source(
    con: duckdb.DuckDBPyConnection,
    source: LogSource,
    input_table: pa.Table,
    output_table: pa.Table,
) -> None:
    rounded = f"round({DEPTH_COLUMN}, {DEPTH_DECIMALS}) AS {DEPTH_COLUMN}"
    for name, table in (("las_input", input_table), ("las_output", output_table)):
        con.register(f"{name}_arrow", table)
        try:
            con.execute(
                f"CREATE OR REPLACE TEMP TABLE {name} AS "
                f"SELECT * REPLACE ({rounded}) FROM {name}_arrow"
            )
        finally:
            con.unregister(f"{name}_arrow")

    input_curves, output_curves = _curves(input_table), _curves(output_table)
    shared = [c for c in input_curves if c in output_curves]
    for name in shared:
        disagreement = con.execute(
            f"SELECT i.{DEPTH_COLUMN}, i.{_q(name)}, o.{_q(name)} "
            f"FROM las_input i JOIN las_output o USING ({DEPTH_COLUMN}) "
            f"WHERE i.{_q(name)} IS DISTINCT FROM o.{_q(name)} "
            f"ORDER BY i.{DEPTH_COLUMN} LIMIT 1"
        ).fetchone()
        if disagreement:
            depth, input_value, output_value = disagreement
            raise CurveDisagreementError(
                f"{source.source_wellbore}: Curve {name} differs between the input "
                f"and the output file at depth {depth} m "
                f"(input {input_value}, output {output_value})"
            )

    selected = (
        [f"i.{_q(c)}" for c in input_curves if c not in shared]
        + [f"o.{_q(c)}" for c in output_curves if c not in shared]
        + [f"coalesce(i.{_q(c)}, o.{_q(c)}) AS {_q(c)}" for c in shared]
    )
    any_value = " OR ".join(
        [f"i.{_q(c)} IS NOT NULL" for c in _not_flags(input_curves)]
        + [f"o.{_q(c)} IS NOT NULL" for c in _not_flags(output_curves)]
    ) or "false"
    con.execute(
        f"INSERT INTO {TABLE} BY NAME "
        f"SELECT $npd AS npd_wellbore_code, $source AS source_wellbore, "
        f"coalesce(i.{DEPTH_COLUMN}, o.{DEPTH_COLUMN}) AS {DEPTH_COLUMN}"
        + "".join(f", {column}" for column in selected)
        + f" FROM las_input i FULL OUTER JOIN las_output o ON i.{DEPTH_COLUMN} = o.{DEPTH_COLUMN} "
        f"WHERE {any_value}",
        {"npd": source.npd_wellbore_code, "source": source.source_wellbore},
    )
