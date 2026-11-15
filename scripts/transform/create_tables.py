"""
Create SQLite Database Tables for Volve Production Data

This script creates the database schema for storing Volve production data using
SQLAlchemy Core (not ORM). The schema consists of three tables:

1. wells - Master table containing unique well entities
2. daily_production - Time-series table with daily production measurements
3. monthly_production - Time-series table with monthly production aggregates

The wells table serves as the parent, with daily_production and monthly_production
as child tables referencing wells via foreign key relationships.
"""

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    Boolean,
    Float,
    Text,
    Date,
    ForeignKey,
    Index,
)

from db_utils import create_database_engine
from constants import (
    # Table names
    TABLE_WELLS,
    TABLE_DAILY_PRODUCTION,
    TABLE_MONTHLY_PRODUCTION,
    # Wells table columns
    WELLS_NPD_WELLBORE_CODE,
    WELLS_WELLBORE_CODE,
    WELLS_WELLBORE_NAME,
    WELLS_NPD_FIELD_CODE,
    WELLS_NPD_FIELD_NAME,
    WELLS_NPD_FACILITY_CODE,
    WELLS_NPD_FACILITY_NAME,
    WELLS_WELLBORE_TYPE,
    WELLS_PURPOSE,
    WELLS_CONTENT,
    WELLS_COMPLETION_YEAR,
    WELLS_PARENT_NPD_WELLBORE_CODE,
    WELLS_HAS_PRODUCTION,
    # Daily production columns
    DAILY_DATE,
    DAILY_NPD_WELLBORE_CODE,
    DAILY_ON_STREAM_HRS,
    DAILY_AVG_DOWNHOLE_PRESSURE,
    DAILY_AVG_DP_TUBING,
    DAILY_AVG_ANNULUS_PRESS,
    DAILY_AVG_WHP_P,
    DAILY_AVG_DOWNHOLE_TEMPERATURE,
    DAILY_AVG_WHT_P,
    DAILY_AVG_CHOKE_SIZE_P,
    DAILY_AVG_CHOKE_UOM,
    DAILY_DP_CHOKE_SIZE,
    DAILY_BORE_OIL_VOL,
    DAILY_BORE_GAS_VOL,
    DAILY_BORE_WAT_VOL,
    DAILY_BORE_WI_VOL,
    DAILY_FLOW_KIND,
    DAILY_WELL_TYPE,
    # Monthly production columns
    MONTHLY_DATE,
    MONTHLY_NPD_WELLBORE_CODE,
    MONTHLY_ON_STREAM,
    MONTHLY_OIL_VOL,
    MONTHLY_GAS_VOL,
    MONTHLY_WATER_VOL,
    MONTHLY_GAS_INJECTION,
    MONTHLY_WATER_INJECTION,
    # Database path
    DATABASE_PATH,
    SEPARATOR_LINE,
)


def create_time_series_indexes(table: Table, date_col: str, wellbore_col: str, prefix: str) -> None:
    """
    Create standard indexes for time-series tables.

    Args:
        table: SQLAlchemy Table object
        date_col: Name of the date column
        wellbore_col: Name of the wellbore code column
        prefix: Prefix for index names (e.g., 'daily', 'monthly')
    """
    Index(f"ix_{prefix}_date", table.c[date_col])
    Index(f"ix_{prefix}_wellbore", table.c[wellbore_col])


def define_wells_table(metadata: MetaData) -> Table:
    """
    Define the wells master table.

    This table contains one row per Wellbore the public register assigns to
    Volve, storing static attributes that don't change over time (identifiers,
    field assignment, facility, the register's classification). The production
    source columns are NULL for a Wellbore without production.

    Primary Key: npd_wellbore_code (unique identifier from Norwegian Petroleum Directorate)

    Args:
        metadata: SQLAlchemy MetaData object

    Returns:
        Table object for wells
    """
    wells = Table(
        TABLE_WELLS,
        metadata,
        Column(
            WELLS_NPD_WELLBORE_CODE,
            Integer,
            primary_key=True,
            comment="Norwegian Petroleum Directorate unique wellbore code",
        ),
        Column(
            WELLS_WELLBORE_CODE,
            Text,
            comment="Well bore code (e.g., 'NO 15/9-F-1 C')",
        ),
        Column(
            WELLS_WELLBORE_NAME,
            Text,
            nullable=False,
            comment="NPD well bore name",
        ),
        Column(
            WELLS_NPD_FIELD_CODE,
            Integer,
            nullable=False,
            comment="NPD field code (3420717 for Volve)",
        ),
        Column(
            WELLS_NPD_FIELD_NAME,
            Text,
            nullable=False,
            comment="Field name",
        ),
        Column(
            WELLS_NPD_FACILITY_CODE,
            Integer,
            comment="NPD facility code",
        ),
        Column(
            WELLS_NPD_FACILITY_NAME,
            Text,
            comment="Facility name",
        ),
        Column(WELLS_WELLBORE_TYPE, Text, nullable=False, comment="Register well type"),
        Column(WELLS_PURPOSE, Text, nullable=False, comment="Register purpose"),
        Column(WELLS_CONTENT, Text, comment="Register content"),
        Column(WELLS_COMPLETION_YEAR, Integer, comment="Register completion year"),
        Column(
            WELLS_PARENT_NPD_WELLBORE_CODE,
            Integer,
            ForeignKey(f"{TABLE_WELLS}.{WELLS_NPD_WELLBORE_CODE}"),
            comment="Wellbore this one was drilled from",
        ),
        Column(
            WELLS_HAS_PRODUCTION,
            Boolean,
            nullable=False,
            comment="Wellbore has production rows",
        ),
    )

    return wells


def define_daily_production_table(metadata: MetaData) -> Table:
    """
    Define the daily production time-series table.

    This table contains daily production measurements and operational metrics
    for each wellbore. Each row represents one day of production for one well.

    Primary Key: (date, npd_wellbore_code)
    Foreign Key: npd_wellbore_code -> wells.npd_wellbore_code

    Args:
        metadata: SQLAlchemy MetaData object

    Returns:
        Table object for daily_production
    """
    daily_production = Table(
        TABLE_DAILY_PRODUCTION,
        metadata,
        Column(
            DAILY_DATE,
            Date,
            primary_key=True,
            nullable=False,
            comment="Production date",
        ),
        Column(
            DAILY_NPD_WELLBORE_CODE,
            Integer,
            ForeignKey(f"{TABLE_WELLS}.{WELLS_NPD_WELLBORE_CODE}"),
            primary_key=True,
            nullable=False,
            comment="Reference to wells table",
        ),
        Column(
            DAILY_ON_STREAM_HRS,
            Float,
            comment="Hours the well was producing",
        ),
        Column(
            DAILY_AVG_DOWNHOLE_PRESSURE,
            Float,
            comment="Average downhole pressure",
        ),
        Column(
            DAILY_AVG_DP_TUBING,
            Float,
            comment="Average differential pressure in tubing",
        ),
        Column(
            DAILY_AVG_ANNULUS_PRESS,
            Float,
            comment="Average annulus pressure",
        ),
        Column(
            DAILY_AVG_WHP_P,
            Float,
            comment="Average wellhead pressure",
        ),
        Column(
            DAILY_AVG_DOWNHOLE_TEMPERATURE,
            Float,
            comment="Average downhole temperature",
        ),
        Column(
            DAILY_AVG_WHT_P,
            Float,
            comment="Average wellhead temperature",
        ),
        Column(
            DAILY_AVG_CHOKE_SIZE_P,
            Float,
            comment="Average choke size as percentage",
        ),
        Column(
            DAILY_AVG_CHOKE_UOM,
            Text,
            comment="Choke unit of measurement",
        ),
        Column(
            DAILY_DP_CHOKE_SIZE,
            Float,
            comment="Differential pressure choke size",
        ),
        Column(
            DAILY_BORE_OIL_VOL,
            Float,
            comment="Oil volume produced from bore",
        ),
        Column(
            DAILY_BORE_GAS_VOL,
            Float,
            comment="Gas volume produced from bore",
        ),
        Column(
            DAILY_BORE_WAT_VOL,
            Float,
            comment="Water volume produced from bore",
        ),
        Column(
            DAILY_BORE_WI_VOL,
            Float,
            comment="Water injection volume (for injection wells)",
        ),
        Column(
            DAILY_FLOW_KIND,
            Text,
            comment="Type of flow (e.g., 'production')",
        ),
        Column(
            DAILY_WELL_TYPE,
            Text,
            comment="Well type (e.g., 'OP' for oil producer, 'WI' for water injector)",
        ),
    )

    create_time_series_indexes(daily_production, DAILY_DATE, DAILY_NPD_WELLBORE_CODE, "daily")

    return daily_production


def define_monthly_production_table(metadata: MetaData) -> Table:
    """
    Define the monthly production time-series table.

    This table contains monthly production aggregates for each wellbore.
    Each row represents one month of production for one well.

    Primary Key: (date, npd_wellbore_code)
    Foreign Key: npd_wellbore_code -> wells.npd_wellbore_code

    Note: Date column represents the first day of the month (YYYY-MM-01)

    Args:
        metadata: SQLAlchemy MetaData object

    Returns:
        Table object for monthly_production
    """
    monthly_production = Table(
        TABLE_MONTHLY_PRODUCTION,
        metadata,
        Column(
            MONTHLY_DATE,
            Date,
            primary_key=True,
            nullable=False,
            comment="First day of production month (YYYY-MM-01)",
        ),
        Column(
            MONTHLY_NPD_WELLBORE_CODE,
            Integer,
            ForeignKey(f"{TABLE_WELLS}.{WELLS_NPD_WELLBORE_CODE}"),
            primary_key=True,
            nullable=False,
            comment="Reference to wells table",
        ),
        Column(
            MONTHLY_ON_STREAM,
            Float,
            comment="Total hours on stream for the month",
        ),
        Column(
            MONTHLY_OIL_VOL,
            Float,
            comment="Oil volume produced (Sm3)",
        ),
        Column(
            MONTHLY_GAS_VOL,
            Float,
            comment="Gas volume produced (Sm3)",
        ),
        Column(
            MONTHLY_WATER_VOL,
            Float,
            comment="Water volume produced (Sm3)",
        ),
        Column(
            MONTHLY_GAS_INJECTION,
            Float,
            comment="Gas injection volume (Sm3)",
        ),
        Column(
            MONTHLY_WATER_INJECTION,
            Float,
            comment="Water injection volume (Sm3)",
        ),
    )

    create_time_series_indexes(monthly_production, MONTHLY_DATE, MONTHLY_NPD_WELLBORE_CODE, "monthly")

    return monthly_production


def create_tables(db_path: str = DATABASE_PATH) -> None:
    """
    Create all database tables in the SQLite database.

    This function:
    1. Creates the database engine
    2. Defines all table schemas
    3. Creates tables in the database (if they don't exist)

    Args:
        db_path: Path to SQLite database file (default from constants)
    """
    print(SEPARATOR_LINE)
    print("CREATING VOLVE PRODUCTION DATABASE SCHEMA")
    print(SEPARATOR_LINE)
    print(f"Database: {db_path}")

    engine, metadata = create_database_engine(db_path, echo=True)

    wells = define_wells_table(metadata)
    daily_production = define_daily_production_table(metadata)
    monthly_production = define_monthly_production_table(metadata)

    metadata.create_all(engine)

    print(f"\n✓ Database schema created successfully")
    print(f"✓ Tables: {TABLE_WELLS}, {TABLE_DAILY_PRODUCTION}, {TABLE_MONTHLY_PRODUCTION}\n")


def print_schema_info() -> None:
    """
    Print human-readable schema information without creating tables.

    Useful for documentation and understanding the database structure.
    """
    print(SEPARATOR_LINE)
    print("VOLVE PRODUCTION DATABASE SCHEMA")
    print(SEPARATOR_LINE)

    print(f"\n1. {TABLE_WELLS.upper()} (Master Table)")
    print("   Purpose: One row per unique wellbore")
    print("   Primary Key: npd_wellbore_code")
    print("   Columns:")
    print("     - npd_wellbore_code (INTEGER, PK)")
    print("     - wellbore_code (TEXT)")
    print("     - wellbore_name (TEXT)")
    print("     - npd_field_code (INTEGER)")
    print("     - npd_field_name (TEXT)")
    print("     - npd_facility_code (INTEGER)")
    print("     - npd_facility_name (TEXT)")
    print("     - wellbore_type, purpose, content (TEXT)")
    print("     - completion_year (INTEGER)")
    print("     - parent_npd_wellbore_code (INTEGER, FK)")
    print("     - has_production (BOOLEAN)")

    print(f"\n2. {TABLE_DAILY_PRODUCTION.upper()} (Time-Series Table)")
    print("   Purpose: Daily production measurements per wellbore")
    print("   Primary Key: (date, npd_wellbore_code)")
    print("   Foreign Key: npd_wellbore_code -> wells.npd_wellbore_code")
    print("   Columns:")
    print("     - date (DATE)")
    print("     - npd_wellbore_code (INTEGER, FK)")
    print("     - Operational metrics (17 columns)")
    print("     - Production volumes (4 columns)")
    print("   Indexes:")
    print("     - ix_daily_date")
    print("     - ix_daily_wellbore")

    print(f"\n3. {TABLE_MONTHLY_PRODUCTION.upper()} (Time-Series Table)")
    print("   Purpose: Monthly production aggregates per wellbore")
    print("   Primary Key: (date, npd_wellbore_code)")
    print("   Foreign Key: npd_wellbore_code -> wells.npd_wellbore_code")
    print("   Columns:")
    print("     - date (DATE, first day of month)")
    print("     - npd_wellbore_code (INTEGER, FK)")
    print("     - on_stream_hours (FLOAT)")
    print("     - Production volumes (3 columns, Sm3)")
    print("     - Injection volumes (2 columns, Sm3)")
    print("   Indexes:")
    print("     - ix_monthly_date")
    print("     - ix_monthly_wellbore")

    print("\nRelationships:")
    print("  wells 1:N daily_production")
    print("  wells 1:N monthly_production")
    print("  (daily_production and monthly_production are independent)")

    print(f"\n{SEPARATOR_LINE}")


if __name__ == "__main__":
    # Print schema documentation
    print_schema_info()

    # Create tables
    print("\n")
    create_tables()
    