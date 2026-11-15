"""
Load Volve Production Data into SQLite Database

This script orchestrates the complete ETL pipeline to load production data
from Excel into the SQLite database using pandas and SQLAlchemy Core.

Pipeline:
1. Join the wellbores of the production source to the Volve wellbores of the
   register snapshot → load wells table
2. Transform and load daily production data → load daily_production table
3. Transform and load monthly production data → load monthly_production table
"""

from pathlib import Path
from typing import Callable, Optional
import pandas as pd
from sqlalchemy import text

from db_utils import create_database_connection
from constants import (
    # Database config
    DATABASE_PATH,
    SOURCE_EXCEL_PATH,
    SHEET_DAILY,
    SHEET_MONTHLY,
    SEPARATOR_LINE,
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
    # Source column names
    SOURCE_DAILY_DATEPRD,
    SOURCE_DAILY_WELL_BORE_CODE,
    SOURCE_DAILY_NPD_WELL_BORE_CODE,
    SOURCE_DAILY_NPD_WELL_BORE_NAME,
    SOURCE_DAILY_NPD_FIELD_CODE,
    SOURCE_DAILY_NPD_FIELD_NAME,
    SOURCE_DAILY_NPD_FACILITY_CODE,
    SOURCE_DAILY_NPD_FACILITY_NAME,
    SOURCE_DAILY_ON_STREAM_HRS,
    SOURCE_DAILY_AVG_DOWNHOLE_PRESSURE,
    SOURCE_DAILY_AVG_DOWNHOLE_TEMPERATURE,
    SOURCE_DAILY_AVG_DP_TUBING,
    SOURCE_DAILY_AVG_ANNULUS_PRESS,
    SOURCE_DAILY_AVG_CHOKE_SIZE_P,
    SOURCE_DAILY_AVG_CHOKE_UOM,
    SOURCE_DAILY_AVG_WHP_P,
    SOURCE_DAILY_AVG_WHT_P,
    SOURCE_DAILY_DP_CHOKE_SIZE,
    SOURCE_DAILY_BORE_OIL_VOL,
    SOURCE_DAILY_BORE_GAS_VOL,
    SOURCE_DAILY_BORE_WAT_VOL,
    SOURCE_DAILY_BORE_WI_VOL,
    SOURCE_DAILY_FLOW_KIND,
    SOURCE_DAILY_WELL_TYPE,
    SOURCE_MONTHLY_WELLBORE_NAME,
    SOURCE_MONTHLY_NPD_CODE,
    SOURCE_MONTHLY_YEAR,
    SOURCE_MONTHLY_MONTH,
    SOURCE_MONTHLY_ON_STREAM,
    SOURCE_MONTHLY_OIL,
    SOURCE_MONTHLY_GAS,
    SOURCE_MONTHLY_WATER,
    SOURCE_MONTHLY_GI,
    SOURCE_MONTHLY_WI,
    # Wellbore register snapshot
    SOURCE_REGISTER_PATHS,
    SOURCE_REGISTER_NAME,
    SOURCE_REGISTER_NPDID,
    SOURCE_REGISTER_FIELD_NAME,
    SOURCE_REGISTER_FIELD_CODE,
    SOURCE_REGISTER_WELL_TYPE,
    SOURCE_REGISTER_PURPOSE,
    SOURCE_REGISTER_CONTENT,
    SOURCE_REGISTER_COMPLETION_YEAR,
    SOURCE_REGISTER_PARENT_NAME,
    VOLVE_NPD_FIELD_CODE,
)


def load_table(
    df: pd.DataFrame,
    table_name: str,
    column_mapping: dict,
    engine,
    transform_fn: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    step_name: str = "",
) -> int:
    """
    Generic ETL function to transform and load data into a database table.

    Args:
        df: Source DataFrame
        table_name: Target table name
        column_mapping: Dictionary mapping source columns to target columns
        engine: SQLAlchemy engine
        transform_fn: Optional function to apply additional transformations
        step_name: Human-readable step name for logging

    Returns:
        Number of records loaded
    """
    production_df = df[list(column_mapping.keys())].copy()
    production_df = production_df.rename(columns=column_mapping)

    if transform_fn:
        production_df = transform_fn(production_df)

    production_df.to_sql(table_name, engine, if_exists='append', index=False)

    print(f"✓ Loaded {len(production_df):,} records into {table_name}")
    return len(production_df)


def read_register(paths=SOURCE_REGISTER_PATHS) -> pd.DataFrame:
    """Read the register snapshot: every wellbore of both CSV exports, as text.

    Values are stripped (the exports pad some empty fields with spaces) and an
    empty value is None.
    """
    columns = [
        SOURCE_REGISTER_NAME,
        SOURCE_REGISTER_NPDID,
        SOURCE_REGISTER_FIELD_NAME,
        SOURCE_REGISTER_FIELD_CODE,
        SOURCE_REGISTER_WELL_TYPE,
        SOURCE_REGISTER_PURPOSE,
        SOURCE_REGISTER_CONTENT,
        SOURCE_REGISTER_COMPLETION_YEAR,
        SOURCE_REGISTER_PARENT_NAME,
    ]
    frames = [
        pd.read_csv(path, usecols=columns, dtype=str, keep_default_na=False)
        for path in paths
    ]
    register = pd.concat(frames, ignore_index=True)
    return register.apply(lambda column: column.str.strip()).replace("", None)


def build_wells(daily_df: pd.DataFrame, register_df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per Wellbore the register assigns to Volve, joined to the production source.

    The production source's columns are kept as they are for the Wellbores it
    names and are NULL for the others, except the name and the field, which
    the register gives for every Wellbore. The parent Wellbore is resolved from
    the register's name to its NPD code. Raises if a producing Wellbore or a
    parent is missing from the Volve Wellbores of the register.
    """
    production = daily_df[[
        SOURCE_DAILY_NPD_WELL_BORE_CODE,
        SOURCE_DAILY_WELL_BORE_CODE,
        SOURCE_DAILY_NPD_WELL_BORE_NAME,
        SOURCE_DAILY_NPD_FIELD_CODE,
        SOURCE_DAILY_NPD_FIELD_NAME,
        SOURCE_DAILY_NPD_FACILITY_CODE,
        SOURCE_DAILY_NPD_FACILITY_NAME,
    ]].drop_duplicates().rename(columns={
        SOURCE_DAILY_NPD_WELL_BORE_CODE: WELLS_NPD_WELLBORE_CODE,
        SOURCE_DAILY_WELL_BORE_CODE: WELLS_WELLBORE_CODE,
        SOURCE_DAILY_NPD_WELL_BORE_NAME: WELLS_WELLBORE_NAME,
        SOURCE_DAILY_NPD_FIELD_CODE: WELLS_NPD_FIELD_CODE,
        SOURCE_DAILY_NPD_FIELD_NAME: WELLS_NPD_FIELD_NAME,
        SOURCE_DAILY_NPD_FACILITY_CODE: WELLS_NPD_FACILITY_CODE,
        SOURCE_DAILY_NPD_FACILITY_NAME: WELLS_NPD_FACILITY_NAME,
    })

    npdid_by_name = dict(zip(register_df[SOURCE_REGISTER_NAME], register_df[SOURCE_REGISTER_NPDID]))
    volve = register_df[
        register_df[SOURCE_REGISTER_FIELD_CODE] == str(VOLVE_NPD_FIELD_CODE)
    ]
    completion_year = pd.to_numeric(volve[SOURCE_REGISTER_COMPLETION_YEAR]).astype("Int64")
    unknown_parents = set(volve[SOURCE_REGISTER_PARENT_NAME].dropna()) - set(npdid_by_name)
    if unknown_parents:
        raise ValueError(f"parent wellbores missing from the register: {sorted(unknown_parents)}")
    register = pd.DataFrame({
        WELLS_NPD_WELLBORE_CODE: volve[SOURCE_REGISTER_NPDID].astype("int64"),
        "register_name": volve[SOURCE_REGISTER_NAME],
        "register_field_code": volve[SOURCE_REGISTER_FIELD_CODE].astype("int64"),
        "register_field_name": volve[SOURCE_REGISTER_FIELD_NAME],
        WELLS_WELLBORE_TYPE: volve[SOURCE_REGISTER_WELL_TYPE],
        WELLS_PURPOSE: volve[SOURCE_REGISTER_PURPOSE],
        WELLS_CONTENT: volve[SOURCE_REGISTER_CONTENT],
        # The register gives 0 for a Wellbore that was never drilled.
        WELLS_COMPLETION_YEAR: completion_year.where(completion_year != 0),
        WELLS_PARENT_NPD_WELLBORE_CODE: pd.array(
            [None if name is None else int(npdid_by_name[name])
             for name in volve[SOURCE_REGISTER_PARENT_NAME]],
            dtype="Int64",
        ),
    })

    missing = set(production[WELLS_NPD_WELLBORE_CODE]) - set(register[WELLS_NPD_WELLBORE_CODE])
    if missing:
        raise ValueError(f"producing wellbores missing from the register: {sorted(missing)}")
    orphans = set(register[WELLS_PARENT_NPD_WELLBORE_CODE].dropna()) - set(register[WELLS_NPD_WELLBORE_CODE])
    if orphans:
        raise ValueError(f"parent wellbores outside Volve in the register: {sorted(orphans)}")

    wells = register.merge(production, on=WELLS_NPD_WELLBORE_CODE, how="left", indicator=True)
    wells[WELLS_HAS_PRODUCTION] = wells.pop("_merge") == "both"
    for column, fallback in (
        (WELLS_WELLBORE_NAME, "register_name"),
        (WELLS_NPD_FIELD_CODE, "register_field_code"),
        (WELLS_NPD_FIELD_NAME, "register_field_name"),
    ):
        wells[column] = wells[column].fillna(wells[fallback])
    wells[WELLS_NPD_FIELD_CODE] = wells[WELLS_NPD_FIELD_CODE].astype("int64")
    wells[WELLS_NPD_FACILITY_CODE] = wells[WELLS_NPD_FACILITY_CODE].astype("Int64")

    return wells[[
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
    ]].sort_values(WELLS_NPD_WELLBORE_CODE, ignore_index=True)


def load_wells_table(daily_df: pd.DataFrame, register_df: pd.DataFrame, engine) -> int:
    """
    Build the wells table from the production source and the register snapshot and load it.

    Args:
        daily_df: DataFrame containing daily production data
        register_df: The register snapshot, from read_register()
        engine: SQLAlchemy engine

    Returns:
        Number of Wellbores loaded
    """
    print(f"\n[1/3] Loading {TABLE_WELLS}...")
    wells_df = build_wells(daily_df, register_df)
    return load_table(wells_df, TABLE_WELLS, {c: c for c in wells_df.columns}, engine)


def load_daily_production_table(daily_df: pd.DataFrame, engine) -> int:
    """
    Transform and load daily production data into database.

    Args:
        daily_df: DataFrame containing daily production data
        engine: SQLAlchemy engine

    Returns:
        Number of records loaded
    """
    print(f"[2/3] Loading {TABLE_DAILY_PRODUCTION}...")

    column_mapping = {
        SOURCE_DAILY_DATEPRD: DAILY_DATE,
        SOURCE_DAILY_NPD_WELL_BORE_CODE: DAILY_NPD_WELLBORE_CODE,
        SOURCE_DAILY_ON_STREAM_HRS: DAILY_ON_STREAM_HRS,
        SOURCE_DAILY_AVG_DOWNHOLE_PRESSURE: DAILY_AVG_DOWNHOLE_PRESSURE,
        SOURCE_DAILY_AVG_DP_TUBING: DAILY_AVG_DP_TUBING,
        SOURCE_DAILY_AVG_ANNULUS_PRESS: DAILY_AVG_ANNULUS_PRESS,
        SOURCE_DAILY_AVG_WHP_P: DAILY_AVG_WHP_P,
        SOURCE_DAILY_AVG_DOWNHOLE_TEMPERATURE: DAILY_AVG_DOWNHOLE_TEMPERATURE,
        SOURCE_DAILY_AVG_WHT_P: DAILY_AVG_WHT_P,
        SOURCE_DAILY_AVG_CHOKE_SIZE_P: DAILY_AVG_CHOKE_SIZE_P,
        SOURCE_DAILY_AVG_CHOKE_UOM: DAILY_AVG_CHOKE_UOM,
        SOURCE_DAILY_DP_CHOKE_SIZE: DAILY_DP_CHOKE_SIZE,
        SOURCE_DAILY_BORE_OIL_VOL: DAILY_BORE_OIL_VOL,
        SOURCE_DAILY_BORE_GAS_VOL: DAILY_BORE_GAS_VOL,
        SOURCE_DAILY_BORE_WAT_VOL: DAILY_BORE_WAT_VOL,
        SOURCE_DAILY_BORE_WI_VOL: DAILY_BORE_WI_VOL,
        SOURCE_DAILY_FLOW_KIND: DAILY_FLOW_KIND,
        SOURCE_DAILY_WELL_TYPE: DAILY_WELL_TYPE,
    }

    def transform_daily(df: pd.DataFrame) -> pd.DataFrame:
        df[DAILY_DATE] = pd.to_datetime(df[DAILY_DATE])
        return df

    return load_table(daily_df, TABLE_DAILY_PRODUCTION, column_mapping, engine, transform_daily)


def load_monthly_production_table(monthly_df: pd.DataFrame, engine) -> int:
    """
    Transform and load monthly production data into database.

    Transformations:
    1. Remove header row (row 0 contains units, not data)
    2. Convert Year + Month → Date (first day of month)
    3. Convert text columns to numeric
    4. Filter out invalid records

    Args:
        monthly_df: DataFrame containing monthly production data
        engine: SQLAlchemy engine

    Returns:
        Number of records loaded
    """
    print(f"[3/3] Loading {TABLE_MONTHLY_PRODUCTION}...")

    monthly_df = monthly_df[1:].copy()

    numeric_columns = [
        SOURCE_MONTHLY_NPD_CODE,
        SOURCE_MONTHLY_YEAR,
        SOURCE_MONTHLY_MONTH,
        SOURCE_MONTHLY_OIL,
        SOURCE_MONTHLY_GAS,
        SOURCE_MONTHLY_WATER,
        SOURCE_MONTHLY_GI,
        SOURCE_MONTHLY_WI,
    ]

    for col in numeric_columns:
        if col in monthly_df.columns:
            monthly_df[col] = pd.to_numeric(monthly_df[col], errors='coerce')

    if SOURCE_MONTHLY_ON_STREAM in monthly_df.columns:
        monthly_df[SOURCE_MONTHLY_ON_STREAM] = pd.to_numeric(
            monthly_df[SOURCE_MONTHLY_ON_STREAM], errors='coerce'
        )

    monthly_df[MONTHLY_DATE] = pd.to_datetime(
        monthly_df[[SOURCE_MONTHLY_YEAR, SOURCE_MONTHLY_MONTH]].rename(
            columns={SOURCE_MONTHLY_YEAR: 'year', SOURCE_MONTHLY_MONTH: 'month'}
        ).assign(day=1)
    )

    column_mapping = {
        MONTHLY_DATE: MONTHLY_DATE,
        SOURCE_MONTHLY_NPD_CODE: MONTHLY_NPD_WELLBORE_CODE,
        SOURCE_MONTHLY_ON_STREAM: MONTHLY_ON_STREAM,
        SOURCE_MONTHLY_OIL: MONTHLY_OIL_VOL,
        SOURCE_MONTHLY_GAS: MONTHLY_GAS_VOL,
        SOURCE_MONTHLY_WATER: MONTHLY_WATER_VOL,
        SOURCE_MONTHLY_GI: MONTHLY_GAS_INJECTION,
        SOURCE_MONTHLY_WI: MONTHLY_WATER_INJECTION,
    }

    def transform_monthly(df: pd.DataFrame) -> pd.DataFrame:
        return df[df[MONTHLY_NPD_WELLBORE_CODE].notna()]

    return load_table(monthly_df, TABLE_MONTHLY_PRODUCTION, column_mapping, engine, transform_monthly)


def run_validation_check(conn, query: str, success_msg: str, error_msg_fn: Callable) -> bool:
    """
    Execute a validation query and report results.

    Args:
        conn: Database connection
        query: SQL query to execute
        success_msg: Message to print if validation passes
        error_msg_fn: Function that takes result and returns error message

    Returns:
        True if validation passes
    """
    result = conn.execute(text(query))
    value = result.scalar() if query.strip().upper().startswith("SELECT COUNT") else result.fetchall()

    if isinstance(value, int):
        if value > 0:
            print(f"   ✗ {error_msg_fn(value)}")
            return False
        print(f"   ✓ {success_msg}")
        return True
    else:
        if len(value) > 0:
            print(f"   ✗ {error_msg_fn(len(value))}")
            return False
        print(f"   ✓ {success_msg}")
        return True


def validate_data_integrity(engine) -> bool:
    """
    Validate referential integrity and data quality after loading.

    Args:
        engine: SQLAlchemy engine

    Returns:
        True if all validations pass
    """
    print(f"\n{SEPARATOR_LINE}")
    print("DATA VALIDATION")
    print(SEPARATOR_LINE)

    all_passed = True

    with engine.connect() as conn:
        for table in [TABLE_WELLS, TABLE_DAILY_PRODUCTION, TABLE_MONTHLY_PRODUCTION]:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            if count == 0:
                print(f"✗ {table} is empty!")
                all_passed = False

        all_passed &= run_validation_check(
            conn,
            f"""SELECT COUNT(*) FROM {TABLE_DAILY_PRODUCTION} d
                LEFT JOIN {TABLE_WELLS} w ON d.{DAILY_NPD_WELLBORE_CODE} = w.{WELLS_NPD_WELLBORE_CODE}
                WHERE w.{WELLS_NPD_WELLBORE_CODE} IS NULL""",
            "All daily production records have valid well references",
            lambda count: f"{count} daily records reference non-existent wells"
        )

        all_passed &= run_validation_check(
            conn,
            f"""SELECT COUNT(*) FROM {TABLE_MONTHLY_PRODUCTION} m
                LEFT JOIN {TABLE_WELLS} w ON m.{MONTHLY_NPD_WELLBORE_CODE} = w.{WELLS_NPD_WELLBORE_CODE}
                WHERE w.{WELLS_NPD_WELLBORE_CODE} IS NULL""",
            "All monthly production records have valid well references",
            lambda count: f"{count} monthly records reference non-existent wells"
        )

        all_passed &= run_validation_check(
            conn,
            f"""SELECT {DAILY_DATE}, {DAILY_NPD_WELLBORE_CODE}, COUNT(*) as cnt
                FROM {TABLE_DAILY_PRODUCTION}
                GROUP BY {DAILY_DATE}, {DAILY_NPD_WELLBORE_CODE}
                HAVING cnt > 1""",
            "No duplicate primary keys in daily_production",
            lambda count: f"Found {count} duplicate date-well combinations in daily_production"
        )

        all_passed &= run_validation_check(
            conn,
            f"""SELECT {MONTHLY_DATE}, {MONTHLY_NPD_WELLBORE_CODE}, COUNT(*) as cnt
                FROM {TABLE_MONTHLY_PRODUCTION}
                GROUP BY {MONTHLY_DATE}, {MONTHLY_NPD_WELLBORE_CODE}
                HAVING cnt > 1""",
            "No duplicate primary keys in monthly_production",
            lambda count: f"Found {count} duplicate date-well combinations in monthly_production"
        )

    return all_passed


def main():
    """
    Main ETL pipeline orchestration.
    """
    print(SEPARATOR_LINE)
    print("VOLVE PRODUCTION DATA ETL PIPELINE")
    print(SEPARATOR_LINE)
    print(f"Source: {SOURCE_EXCEL_PATH}")
    print(f"Target: {DATABASE_PATH}\n")

    if not Path(SOURCE_EXCEL_PATH).exists():
        print(f"✗ ERROR: Source file not found: {SOURCE_EXCEL_PATH}")
        print("Please ensure the Volve dataset is downloaded and placed in the data/ directory")
        return

    missing_register = [p for p in SOURCE_REGISTER_PATHS if not Path(p).exists()]
    if missing_register:
        print(f"✗ ERROR: Register snapshot not found: {', '.join(missing_register)}")
        print("Run `uv run python -m scripts.raw_repo.volve fetch-register` first")
        return

    if not Path(DATABASE_PATH).exists():
        print(f"✗ ERROR: Database not found: {DATABASE_PATH}")
        print("Please run create_tables.py first to create the database schema")
        return

    engine = create_database_connection(DATABASE_PATH)

    print(f"Loading Excel file: {SHEET_DAILY}, {SHEET_MONTHLY}")
    daily_df = pd.read_excel(SOURCE_EXCEL_PATH, sheet_name=SHEET_DAILY)
    monthly_df = pd.read_excel(SOURCE_EXCEL_PATH, sheet_name=SHEET_MONTHLY)
    register_df = read_register()

    try:
        wells_count = load_wells_table(daily_df, register_df, engine)
        daily_count = load_daily_production_table(daily_df, engine)
        monthly_count = load_monthly_production_table(monthly_df, engine)

        validation_passed = validate_data_integrity(engine)

        print(f"\n{SEPARATOR_LINE}")
        print("ETL PIPELINE COMPLETE")
        print(SEPARATOR_LINE)
        print(f"Wells: {wells_count} | Daily: {daily_count:,} | Monthly: {monthly_count:,}")
        print(f"Validation: {'✓ PASSED' if validation_passed else '✗ FAILED'}")
        print(f"Database: {DATABASE_PATH}")
        print(SEPARATOR_LINE)

    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        raise


if __name__ == "__main__":
    main()
