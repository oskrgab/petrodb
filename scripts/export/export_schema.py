"""
Export Database Schema Metadata

This script extracts the database schema (tables, columns, relationships,
constraints) from the SQLite database using SQLAlchemy reflection and exports
it in multiple formats:

1. schema.sql - DDL statements to recreate the database structure
2. schema.json - Machine-readable schema metadata
3. schema.md - Human-readable documentation

These files help consumers of the parquet files understand the data structure
and relationships without needing access to the original database.

The log tables are not in the SQLite database: their Parquet is built from
raw log files by the Volve log pipeline (``scripts.run_pipeline.volve_logs``).
Their definitions are added to the reflected metadata by ``add_log_tables``:
the interpretation table, one column per Curve described in
``volve_descriptions``, and the Curve catalog ``log_curves``. Each of their
columns also states its unit (``unit`` in schema.json, a Unit column in
schema.md); a Curve's unit is the one the committed unit table
(``scripts.transform.volve_logs.units``) documents for it. The export fails
if a Curve has no documented unit. Tables without units keep their layout.

SQLite keeps no column comments, so table and column descriptions cannot be
reflected. They come from ``volve_descriptions``; the export fails if a
reflected column has no description or a description names a column that
does not exist. The Landing reads them from the generated schema.md.

Run from the repo root::

    uv run -m scripts.export.export_schema
"""

import json
from pathlib import Path

from sqlalchemy import (
    DOUBLE,
    INTEGER,
    TEXT,
    Column,
    ForeignKey,
    MetaData,
    Table,
    create_engine,
)
from sqlalchemy.schema import CreateTable, CreateIndex

from scripts.export.volve_descriptions import COLUMN_DESCRIPTIONS, TABLE_DESCRIPTIONS
from scripts.transform.volve_logs.interpretation_builder import DOCUMENTED_CURVES
from scripts.transform.volve_logs.units import CURVE_UNITS
from scripts.transform.constants import DATABASE_PATH

REPO_ROOT = Path(__file__).resolve().parents[2]

# Output directory: the published Volve Dataset
SCHEMA_OUTPUT_DIR = REPO_ROOT / "parquet" / "volve"

# Units of the columns of the tables that document them; a column absent here
# has no unit (``null`` in schema.json, an em dash in schema.md).
TABLE_UNITS = {
    "petrophysical_interpretation": {"depth_md": "m", **CURVE_UNITS},
    "log_curves": {"first_depth_md": "m", "last_depth_md": "m"},
}


def check_descriptions(
    columns: dict[str, list[str]], descriptions: dict[str, dict[str, str]]
) -> None:
    """Fail unless every reflected column, and only those, has a description."""
    problems = []
    for table in sorted(set(columns) | set(descriptions)):
        have = set(columns.get(table, []))
        described = {c for c, text in descriptions.get(table, {}).items() if text}
        problems += [f"{table}.{c}: no description" for c in sorted(have - described)]
        problems += [f"{table}.{c}: no such column" for c in sorted(described - have)]
    if problems:
        raise ValueError("column descriptions: " + "; ".join(problems))


def check_curve_units(curves: tuple[str, ...], units: dict[str, str]) -> None:
    """Fail unless every documented Curve, and only those, has a documented unit."""
    problems = [f"{c}: no documented unit" for c in curves if c not in units]
    problems += [f"{c}: unit for a Curve with no description" for c in units if c not in curves]
    if problems:
        raise ValueError("Curve units: " + "; ".join(problems))


def reflect_schema(engine) -> MetaData:
    """Reflect the database schema using SQLAlchemy."""
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return metadata


def add_log_tables(metadata: MetaData) -> None:
    """Add the log tables, which the SQLite database does not hold, to ``metadata``."""
    Table(
        "petrophysical_interpretation",
        metadata,
        Column(
            "npd_wellbore_code",
            INTEGER,
            ForeignKey("wells.npd_wellbore_code"),
            nullable=False,
        ),
        Column("source_wellbore", TEXT, primary_key=True),
        Column("depth_md", DOUBLE, primary_key=True),
        *(Column(name, DOUBLE) for name in DOCUMENTED_CURVES),
    )
    Table(
        "log_curves",
        metadata,
        Column("table_name", TEXT, primary_key=True),
        Column(
            "npd_wellbore_code",
            INTEGER,
            ForeignKey("wells.npd_wellbore_code"),
            nullable=False,
        ),
        Column("source_wellbore", TEXT, primary_key=True),
        Column("mnemonic", TEXT, primary_key=True),
        Column("curve_kind", TEXT, nullable=False),
        Column("unit", TEXT, nullable=False),
        Column("source_unit", TEXT, nullable=False),
        Column("first_depth_md", DOUBLE, nullable=False),
        Column("last_depth_md", DOUBLE, nullable=False),
        Column("sample_count", INTEGER, nullable=False),
        Column("source_file", TEXT, nullable=False),
    )


def get_table_info(table: Table) -> list[dict]:
    """Get column information from a SQLAlchemy Table object."""
    columns = []
    units = TABLE_UNITS.get(table.name)
    for col in table.columns:
        unit = {"unit": units.get(col.name)} if units is not None else {}
        columns.append({
            "name": col.name,
            "type": str(col.type),
            **unit,
            "not_null": not col.nullable,
            "default_value": str(col.default.arg) if col.default else None,
            "primary_key": col.primary_key,
            # Always null (SQLite keeps no comments), but published in
            # schema.json since before descriptions existed: dropping the key
            # would change the published document.
            "comment": col.comment,
            "description": COLUMN_DESCRIPTIONS[table.name][col.name],
        })
    return columns


def get_foreign_keys(table: Table) -> list[dict]:
    """Get foreign key relationships from a SQLAlchemy Table object."""
    foreign_keys = []
    for fk in table.foreign_keys:
        foreign_keys.append({
            "column": fk.parent.name,
            "references_table": fk.column.table.name,
            "references_column": fk.column.name
        })
    return foreign_keys


def sorted_indexes(table: Table) -> list:
    """table.indexes is a set: sort it so the published documents are stable."""
    return sorted(table.indexes, key=lambda i: i.name)


def get_indexes(table: Table) -> list[dict]:
    """Get indexes from a SQLAlchemy Table object."""
    indexes = []
    for index in sorted_indexes(table):
        indexes.append({
            "name": index.name,
            "unique": index.unique,
            "columns": [col.name for col in index.columns]
        })
    return indexes


def export_schema_json(metadata: MetaData, output_path: Path):
    """Export schema as JSON for machine consumption."""
    schema = {
        "database": "volve.db",
        "description": "Equinor Volve production dataset",
        "tables": {}
    }

    for table_name, table in metadata.tables.items():
        schema["tables"][table_name] = {
            "description": TABLE_DESCRIPTIONS[table_name],
            "columns": get_table_info(table),
            "foreign_keys": get_foreign_keys(table),
            "indexes": get_indexes(table)
        }

    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2)

    print(f"✓ Exported JSON schema: {output_path}")


def export_schema_sql(metadata: MetaData, engine, output_path: Path):
    """Export schema as SQL DDL statements using SQLAlchemy."""
    ddl_statements = []

    # Generate CREATE TABLE statements
    for table_name, table in sorted(metadata.tables.items()):
        create_table_stmt = str(CreateTable(table).compile(engine))
        ddl_statements.append(create_table_stmt + ";")

    # Generate CREATE INDEX statements
    for table_name, table in sorted(metadata.tables.items()):
        for index in sorted_indexes(table):
            create_index_stmt = str(CreateIndex(index).compile(engine))
            ddl_statements.append(create_index_stmt + ";")

    content = "-- Volve Database Schema\n"
    content += "-- Auto-generated schema export using SQLAlchemy\n"
    content += "-- This file contains DDL statements to recreate the database structure\n\n"
    content += "\n\n".join(ddl_statements)

    with open(output_path, 'w') as f:
        f.write(content)

    print(f"✓ Exported SQL schema: {output_path}")


def export_schema_markdown(metadata: MetaData, output_path: Path):
    """Export schema as human-readable markdown documentation."""
    content = "# Volve Database Schema\n\n"
    content += "This document describes the structure of the Volve production database.\n\n"
    content += "## Tables\n\n"

    for table_name, table in sorted(metadata.tables.items()):
        content += f"### `{table_name}`\n\n"
        content += f"{TABLE_DESCRIPTIONS[table_name]}\n\n"

        # Columns
        columns = get_table_info(table)
        content += "**Columns:**\n\n"
        has_units = table_name in TABLE_UNITS
        headers = ["Column", "Type", *(["Unit"] if has_units else []),
                   "Nullable", "Primary Key", "Description"]
        content += "| " + " | ".join(headers) + " |\n"
        content += "|" + "|".join("-" * (len(h) + 2) for h in headers) + "|\n"

        for col in columns:
            nullable = "Yes" if not col["not_null"] else "No"
            pk = "✓" if col["primary_key"] else ""
            unit = f" {col['unit'] or '—'} |" if has_units else ""
            content += (
                f"| `{col['name']}` | {col['type']} |{unit} {nullable} | {pk} "
                f"| {col['description']} |\n"
            )

        content += "\n"

        # Foreign keys
        foreign_keys = get_foreign_keys(table)
        if foreign_keys:
            content += "**Foreign Keys:**\n\n"
            for fk in foreign_keys:
                content += f"- `{fk['column']}` → `{fk['references_table']}.{fk['references_column']}`\n"
            content += "\n"

        # Indexes
        indexes = get_indexes(table)
        if indexes:
            content += "**Indexes:**\n\n"
            for idx in indexes:
                unique = " (UNIQUE)" if idx["unique"] else ""
                cols = ", ".join(idx["columns"])
                content += f"- `{idx['name']}`{unique}: {cols}\n"
            content += "\n"

        content += "---\n\n"

    # Add relationship diagram section
    content += "## Relationships\n\n"
    content += "```\n"
    for table_name, table in sorted(metadata.tables.items()):
        foreign_keys = get_foreign_keys(table)
        if foreign_keys:
            for fk in foreign_keys:
                content += f"{table_name}.{fk['column']} → {fk['references_table']}.{fk['references_column']}\n"
    content += "```\n"

    with open(output_path, 'w') as f:
        f.write(content)

    print(f"✓ Exported Markdown schema: {output_path}")


def export_all_schemas(output_dir: Path = SCHEMA_OUTPUT_DIR):
    """Export database schema in all formats using SQLAlchemy reflection."""
    print("="*80)
    print("EXPORTING DATABASE SCHEMA")
    print("="*80)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Connect to database using SQLAlchemy
    database = REPO_ROOT / DATABASE_PATH
    print(f"\nConnecting to: {database}")
    engine = create_engine(f"sqlite:///{database}")

    # Reflect the schema
    print("Reflecting database schema...")
    metadata = reflect_schema(engine)
    print(f"  → Found {len(metadata.tables)} tables")
    add_log_tables(metadata)
    check_curve_units(DOCUMENTED_CURVES, CURVE_UNITS)
    check_descriptions(
        {name: [c.name for c in t.columns] for name, t in metadata.tables.items()},
        COLUMN_DESCRIPTIONS,
    )

    # Export in different formats
    print("\nExporting schema...")
    export_schema_json(metadata, output_dir / "schema.json")
    export_schema_sql(metadata, engine, output_dir / "schema.sql")
    export_schema_markdown(metadata, output_dir / "schema.md")

    engine.dispose()

    print("\n" + "="*80)
    print("SCHEMA EXPORT COMPLETE")
    print("="*80)
    print(f"\nSchema files exported to: {output_dir}/")
    print("  - schema.json (machine-readable)")
    print("  - schema.sql (DDL statements)")
    print("  - schema.md (human-readable documentation)")


if __name__ == "__main__":
    export_all_schemas()
