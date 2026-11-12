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

SQLite keeps no column comments, so table and column descriptions cannot be
reflected. They live here as module-level constants, the single source of truth
for what each published column holds; the export fails if a reflected column
has no description or a description names a column that does not exist. The
Landing reads them from the generated schema.md.

Run from the repo root::

    uv run -m scripts.export.export_schema
"""

import json
from pathlib import Path

from sqlalchemy import MetaData, create_engine, Table
from sqlalchemy.schema import CreateTable, CreateIndex

from scripts.transform.constants import DATABASE_PATH

REPO_ROOT = Path(__file__).resolve().parents[2]

# Output directory: the published Volve Dataset
SCHEMA_OUTPUT_DIR = REPO_ROOT / "parquet" / "volve"

TABLE_DESCRIPTIONS = {
    "wells": (
        "One row per wellbore in the Volve field: its identifiers and the "
        "field and facility it belongs to. Seven wellbores, all produced "
        "through the Mærsk Inspirer production unit."
    ),
    "daily_production": (
        "Daily measurements per wellbore, from Equinor's daily production "
        "report: hours on stream, pressures, temperatures, choke opening and "
        "the volumes produced or injected. One row per `(date, "
        "npd_wellbore_code)`. Volumes are in standard cubic metres (Sm³)."
    ),
    "monthly_production": (
        "Monthly volumes per wellbore, from Equinor's monthly production "
        "report. One row per `(date, npd_wellbore_code)`, where `date` is the "
        "first day of the month. Volumes are in standard cubic metres (Sm³)."
    ),
}

# Plain-English descriptions for every published column. The source column in
# Equinor's "Volve production data.xlsx" is named where the mapping helps.
COLUMN_DESCRIPTIONS = {
    "wells": {
        "npd_wellbore_code": (
            "Wellbore identifier assigned by the Norwegian Offshore Directorate "
            "(formerly the Norwegian Petroleum Directorate, NPD). The key "
            "every production row joins on."
        ),
        "wellbore_code": (
            "Equinor's wellbore code, prefixed with the country (e.g. "
            "`NO 15/9-F-12 H`)."
        ),
        "wellbore_name": (
            "NPD wellbore name (e.g. `15/9-F-12`, a well in block 15/9). "
            "Use this to label wells."
        ),
        "npd_field_code": "NPD field identifier. The same value on every row: Volve.",
        "npd_field_name": "Field name: `VOLVE` on every row.",
        "npd_facility_code": "NPD identifier of the facility the wellbore produced through.",
        "npd_facility_name": (
            "Facility the wellbore produced through: the `MÆRSK INSPIRER` "
            "jack-up production unit on every row."
        ),
    },
    "daily_production": {
        "date": (
            "Production day (source `DATEPRD`). Stored in the Parquet file "
            "as a timestamp at midnight."
        ),
        "npd_wellbore_code": "Wellbore the row belongs to. Joins to `wells`.",
        "on_stream_hours": (
            "Hours the wellbore was producing or injecting that day "
            "(`ON_STREAM_HRS`). Up to 25 on the day the clocks go back."
        ),
        "avg_downhole_pressure": (
            "Average pressure at the downhole gauge over the day, in bar "
            "(`AVG_DOWNHOLE_PRESSURE`)."
        ),
        "avg_dp_tubing": (
            "Average pressure drop along the production tubing, from the "
            "downhole gauge to the wellhead, in bar (`AVG_DP_TUBING`)."
        ),
        "avg_annulus_pressure": (
            "Average pressure in the annulus between tubing and casing, in bar "
            "(`AVG_ANNULUS_PRESS`)."
        ),
        "avg_wellhead_pressure": "Average pressure at the wellhead, in bar (`AVG_WHP_P`).",
        "avg_downhole_temperature": (
            "Average temperature at the downhole gauge, in °C "
            "(`AVG_DOWNHOLE_TEMPERATURE`)."
        ),
        "avg_wellhead_temperature": "Average temperature at the wellhead, in °C (`AVG_WHT_P`).",
        "avg_choke_size_percent": (
            "Average production choke opening, as a percentage of fully open "
            "(`AVG_CHOKE_SIZE_P`)."
        ),
        "avg_choke_unit": (
            "Unit of `avg_choke_size_percent`: `%`, or NULL on injection rows "
            "(`AVG_CHOKE_UOM`)."
        ),
        "dp_choke_size": (
            "Pressure drop across the production choke, in bar "
            "(`DP_CHOKE_SIZE`)."
        ),
        "oil_volume": "Oil produced from the wellbore that day, in Sm³ (`BORE_OIL_VOL`).",
        "gas_volume": "Gas produced from the wellbore that day, in Sm³ (`BORE_GAS_VOL`).",
        "water_volume": (
            "Water produced from the wellbore that day, in Sm³ "
            "(`BORE_WAT_VOL`). A few rows are negative, kept as the source "
            "reports them."
        ),
        "water_injection_volume": (
            "Water injected into the wellbore that day, in Sm³ "
            "(`BORE_WI_VOL`). Filled on injection rows and on a handful of "
            "production rows."
        ),
        "flow_kind": "Direction of flow that day: `production` or `injection` (`FLOW_KIND`).",
        "well_type": (
            "Role of the wellbore that day: `OP` oil producer, `WI` water "
            "injector (`WELL_TYPE`). Can change over a wellbore's life."
        ),
    },
    "monthly_production": {
        "date": (
            "First day of the month the volumes cover, built from the source "
            "`Year` and `Month`. Stored in the Parquet file as a timestamp."
        ),
        "npd_wellbore_code": "Wellbore the row belongs to. Joins to `wells`.",
        "on_stream_hours": "Hours the wellbore was on stream in the month (`On Stream`).",
        "oil_volume_sm3": "Oil produced in the month, in Sm³ (`Oil`).",
        "gas_volume_sm3": "Gas produced in the month, in Sm³ (`Gas`).",
        "water_volume_sm3": "Water produced in the month, in Sm³ (`Water`).",
        "gas_injection_sm3": (
            "Gas injected in the month, in Sm³ (`GI`). Empty in every row of "
            "the source."
        ),
        "water_injection_sm3": "Water injected in the month, in Sm³ (`WI`).",
    },
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
        raise ValueError("Volve column descriptions: " + "; ".join(problems))


def reflect_schema(engine) -> MetaData:
    """Reflect the database schema using SQLAlchemy."""
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return metadata


def get_table_info(table: Table) -> list[dict]:
    """Get column information from a SQLAlchemy Table object."""
    columns = []
    for col in table.columns:
        columns.append({
            "name": col.name,
            "type": str(col.type),
            "not_null": not col.nullable,
            "default_value": str(col.default.arg) if col.default else None,
            "primary_key": col.primary_key,
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
        content += "| Column | Type | Nullable | Primary Key | Description |\n"
        content += "|--------|------|----------|-------------|-------------|\n"

        for col in columns:
            nullable = "Yes" if not col["not_null"] else "No"
            pk = "✓" if col["primary_key"] else ""
            content += (
                f"| `{col['name']}` | {col['type']} | {nullable} | {pk} "
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
