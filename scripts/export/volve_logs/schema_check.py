"""Compare the written ``petrophysical_interpretation.parquet`` with the committed ``schema.json``.

The table is not in git, so nothing else would catch the schema documents and
the published bytes drifting apart. The check fails on any difference in
column names, order, types or nullability:

- names and order must be the same list;
- each type must be the DuckDB type ``SCHEMA_TYPES`` maps the declared type to
  (``schema.json`` names types the way the SQLite schema export does);
- a column declared NOT NULL must hold no NULL, and a column the Parquet
  schema marks required must be declared NOT NULL. DuckDB writes every
  column optional, so for a DuckDB-written file NOT NULL is checked against
  the values.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from scripts.export.volve_logs.validator import PrePublishCheckError
from scripts.transform.volve_logs.interpretation_builder import TABLE
from scripts.transform.volve_logs.sql import identifier, path_literal

# Declared type in schema.json -> the DuckDB type of the column read back.
SCHEMA_TYPES = {"INTEGER": "BIGINT", "TEXT": "VARCHAR", "DOUBLE": "DOUBLE"}


class SchemaMismatchError(PrePublishCheckError):
    """The written table differs from the committed ``schema.json``."""


def check(parquet: Path, schema: Path) -> None:
    """Raise ``SchemaMismatchError`` listing every way ``parquet`` differs from ``schema``."""
    declared = json.loads(Path(schema).read_text())["tables"][TABLE]["columns"]
    source = f"read_parquet({path_literal(parquet)})"
    with duckdb.connect() as con:
        written = [row[:2] for row in con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()]
        types = dict(written)
        required = {
            name
            for name, repetition in con.execute(
                f"SELECT name, repetition_type FROM parquet_schema({path_literal(parquet)})"
            ).fetchall()
            if repetition == "REQUIRED"
        }
        not_null = [c["name"] for c in declared if c["not_null"] and c["name"] in types]
        with_nulls = set()
        if not_null:
            counts = con.execute(
                "SELECT "
                + ", ".join(f"count(*) FILTER (WHERE {identifier(c)} IS NULL)" for c in not_null)
                + f" FROM {source}"
            ).fetchone()
            with_nulls = {name for name, n in zip(not_null, counts) if n}

    written_names = [name for name, _ in written]
    declared_names = [c["name"] for c in declared]
    problems = []
    if written_names != declared_names:
        problems.append(
            f"columns are {', '.join(written_names)}; "
            f"schema.json declares {', '.join(declared_names)}"
        )
    for column in declared:
        name = column["name"]
        if name not in types:
            continue
        if SCHEMA_TYPES.get(column["type"]) != types[name]:
            problems.append(f"{name}: {types[name]} in the file, schema.json declares {column['type']}")
        if name in with_nulls:
            problems.append(f"{name}: holds NULL, schema.json declares NOT NULL")
        if name in required and not column["not_null"]:
            problems.append(f"{name}: required in the file, schema.json declares it nullable")
    if problems:
        raise SchemaMismatchError(f"{TABLE} differs from {schema}: " + "; ".join(problems))
