"""Join each source's LAS or DLIS files into the ``petrophysical_interpretation`` table.

The input and output files of a pair share a depth grid, so they are joined on
``depth_md`` (rounded to four decimals): Input curves and Interpreted curves
side by side, one row per depth sample, at the source depths. A mnemonic in
both files becomes one column, and the build fails if the two files disagree
on it at any depth they share. A source with an input file only has every
Interpreted curve NULL. A single interpretation file (the 15/9-19 sources) is
divided into its Input and its Interpreted curves by the Curve catalog's
committed list, ``curve_catalog.SINGLE_FILE_CURVE_KINDS``, and the two halves
are joined like a pair; a mnemonic the list does not classify fails the build.

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

from dataclasses import dataclass
from pathlib import Path, PurePath

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from scripts.export.volve_descriptions import COLUMN_DESCRIPTIONS
from scripts.transform.volve_logs import curve_catalog, units
from scripts.transform.volve_logs.dlis_reader import read_dlis
from scripts.transform.volve_logs.las_reader import DEPTH_COLUMN, read_las
from scripts.transform.volve_logs.sources import (
    DLIS,
    LAS,
    SINGLE_FILE_SOURCES,
    SOURCES,
    LogSource,
    SingleFileSource,
    SourceFileError,
)
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


class UnclassifiedCurveError(Exception):
    """A single interpretation file carries a Curve the committed list does not classify."""


@dataclass(frozen=True)
class _ReadSource:
    """One ``source_wellbore`` as read: the table of its input file and the
    table of its Interpreted curves, each with the file it came from (a path
    within the Raw repo). For a pair the second is the output file, which may
    repeat Input curves; for a single file both halves name that file; an
    input-only source has no second file (``None``) and an empty table."""

    source_wellbore: str
    npd_wellbore_code: int
    input_file: PurePath
    input_table: pa.Table
    interpreted_file: PurePath | None
    interpreted_table: pa.Table


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
    read = [_read_pair(source, raw_dir) for source in SOURCES] + [
        _read_single_file(source, raw_dir) for source in SINGLE_FILE_SOURCES
    ]
    present = {
        name
        for source in read
        for name in _curves(source.input_table) + _curves(source.interpreted_table)
    }
    undocumented = sorted(present - set(DOCUMENTED_CURVES))
    if undocumented:
        raise UndocumentedCurveError(
            f"Curve(s) with no description in volve_descriptions: {', '.join(undocumented)}"
        )
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
    for source in read:
        _insert_source(con, source)
        _record_curve_sources(con, source)
        expected_rows[source.source_wellbore] = len(
            _non_empty_depths(source.input_table) | _non_empty_depths(source.interpreted_table)
        )
    return expected_rows


# An empty root gives each path within the Raw repo.
_IN_RAW_REPO = Path()


def _read_pair(source: LogSource, raw_dir: Path) -> _ReadSource:
    """The input and output files of ``source``, each checked for its units."""
    read = READERS[source.file_format]
    input_table = read(source.input_path(raw_dir))
    output_table = _read_output(source, raw_dir)
    units.check(source.input_path(raw_dir), input_table)
    units.check(source.output_path(raw_dir), output_table)
    return _ReadSource(
        source.source_wellbore,
        source.npd_wellbore_code,
        source.input_path(_IN_RAW_REPO),
        input_table,
        source.output_path(_IN_RAW_REPO),
        output_table,
    )


def _read_single_file(source: SingleFileSource, raw_dir: Path) -> _ReadSource:
    """The one LAS file of ``source``, checked for its units and divided by Curve kind."""
    path = source.path(raw_dir)
    table = read_las(path)
    units.check(path, table)
    input_table, interpreted_table = _split_by_kind(path, table)
    file = source.path(_IN_RAW_REPO)
    return _ReadSource(
        source.source_wellbore,
        source.npd_wellbore_code,
        file,
        input_table,
        file,
        interpreted_table,
    )


def _split_by_kind(path: Path, table: pa.Table) -> tuple[pa.Table, pa.Table]:
    """``table``, read from the single file at ``path``, as its Input curves
    and its Interpreted curves, each keeping the depth column."""
    kinds = curve_catalog.SINGLE_FILE_CURVE_KINDS
    curves = _curves(table)
    unclassified = [name for name in curves if name not in kinds]
    if unclassified:
        raise UnclassifiedCurveError(
            f"{path}: Curve(s) {', '.join(unclassified)} not listed as Input or "
            "Interpreted in curve_catalog.SINGLE_FILE_CURVE_KINDS"
        )

    def of_kind(kind: str) -> pa.Table:
        return table.select([DEPTH_COLUMN, *(c for c in curves if kinds[c] == kind)])

    return of_kind(curve_catalog.INPUT), of_kind(curve_catalog.INTERPRETED)


def _record_curve_sources(con: duckdb.DuckDBPyConnection, source: _ReadSource) -> None:
    """Note each Curve's file for the Curve catalog: the input file first, so a
    mnemonic in both files is an Input curve named after the input file."""
    files = [(curve_catalog.INPUT, source.input_file, source.input_table)]
    if source.interpreted_file is not None:
        files.append(
            (curve_catalog.INTERPRETED, source.interpreted_file, source.interpreted_table)
        )
    curve_catalog.record(con, TABLE, source.source_wellbore, files)


def _insert_source(con: duckdb.DuckDBPyConnection, source: _ReadSource) -> None:
    input_table, output_table = source.input_table, source.interpreted_table
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
