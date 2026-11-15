"""
Database Constants and Column Definitions

This module defines reusable constants for database table and column names
used throughout the Volve production data transformation and analysis pipeline.

All column names are defined as constants to:
1. Avoid typos and string literal errors
2. Enable IDE autocomplete and refactoring
3. Maintain consistency across transformation and analysis scripts
4. Serve as documentation for the database schema
"""

# =============================================================================
# TABLE NAMES
# =============================================================================

TABLE_WELLS = "wells"
TABLE_DAILY_PRODUCTION = "daily_production"
TABLE_MONTHLY_PRODUCTION = "monthly_production"


# =============================================================================
# WELLS TABLE COLUMNS (Master table for unique well entities)
# =============================================================================

# Primary key
WELLS_NPD_WELLBORE_CODE = "npd_wellbore_code"

# Well identification
WELLS_WELLBORE_CODE = "wellbore_code"
WELLS_WELLBORE_NAME = "wellbore_name"

# Field information
WELLS_NPD_FIELD_CODE = "npd_field_code"
WELLS_NPD_FIELD_NAME = "npd_field_name"

# Facility information
WELLS_NPD_FACILITY_CODE = "npd_facility_code"
WELLS_NPD_FACILITY_NAME = "npd_facility_name"

# From the wellbore register snapshot
WELLS_WELLBORE_TYPE = "wellbore_type"
WELLS_PURPOSE = "purpose"
WELLS_CONTENT = "content"
WELLS_COMPLETION_YEAR = "completion_year"
WELLS_PARENT_NPD_WELLBORE_CODE = "parent_npd_wellbore_code"

# True for a Wellbore with rows in the production tables
WELLS_HAS_PRODUCTION = "has_production"


# =============================================================================
# DAILY PRODUCTION TABLE COLUMNS
# =============================================================================

# Primary key components & foreign key
DAILY_DATE = "date"
DAILY_NPD_WELLBORE_CODE = "npd_wellbore_code"

# Operational metrics - time on stream
DAILY_ON_STREAM_HRS = "on_stream_hours"

# Operational metrics - pressure measurements
DAILY_AVG_DOWNHOLE_PRESSURE = "avg_downhole_pressure"
DAILY_AVG_DP_TUBING = "avg_dp_tubing"
DAILY_AVG_ANNULUS_PRESS = "avg_annulus_pressure"
DAILY_AVG_WHP_P = "avg_wellhead_pressure"

# Operational metrics - temperature
DAILY_AVG_DOWNHOLE_TEMPERATURE = "avg_downhole_temperature"
DAILY_AVG_WHT_P = "avg_wellhead_temperature"

# Operational metrics - choke
DAILY_AVG_CHOKE_SIZE_P = "avg_choke_size_percent"
DAILY_AVG_CHOKE_UOM = "avg_choke_unit"
DAILY_DP_CHOKE_SIZE = "dp_choke_size"

# Production volumes
DAILY_BORE_OIL_VOL = "oil_volume"
DAILY_BORE_GAS_VOL = "gas_volume"
DAILY_BORE_WAT_VOL = "water_volume"
DAILY_BORE_WI_VOL = "water_injection_volume"

# Classification
DAILY_FLOW_KIND = "flow_kind"
DAILY_WELL_TYPE = "well_type"


# =============================================================================
# MONTHLY PRODUCTION TABLE COLUMNS
# =============================================================================

# Primary key components & foreign key
MONTHLY_DATE = "date"
MONTHLY_NPD_WELLBORE_CODE = "npd_wellbore_code"

# Operational metric
MONTHLY_ON_STREAM = "on_stream_hours"

# Production volumes (Sm3 - Standard cubic meters)
MONTHLY_OIL_VOL = "oil_volume_sm3"
MONTHLY_GAS_VOL = "gas_volume_sm3"
MONTHLY_WATER_VOL = "water_volume_sm3"

# Injection volumes (Sm3)
MONTHLY_GAS_INJECTION = "gas_injection_sm3"
MONTHLY_WATER_INJECTION = "water_injection_sm3"


# =============================================================================
# SOURCE FILE COLUMN NAMES (from Excel)
# =============================================================================
# These map to the original Excel column names for transformation scripts

# Daily production source columns
SOURCE_DAILY_DATEPRD = "DATEPRD"
SOURCE_DAILY_WELL_BORE_CODE = "WELL_BORE_CODE"
SOURCE_DAILY_NPD_WELL_BORE_CODE = "NPD_WELL_BORE_CODE"
SOURCE_DAILY_NPD_WELL_BORE_NAME = "NPD_WELL_BORE_NAME"
SOURCE_DAILY_NPD_FIELD_CODE = "NPD_FIELD_CODE"
SOURCE_DAILY_NPD_FIELD_NAME = "NPD_FIELD_NAME"
SOURCE_DAILY_NPD_FACILITY_CODE = "NPD_FACILITY_CODE"
SOURCE_DAILY_NPD_FACILITY_NAME = "NPD_FACILITY_NAME"
SOURCE_DAILY_ON_STREAM_HRS = "ON_STREAM_HRS"
SOURCE_DAILY_AVG_DOWNHOLE_PRESSURE = "AVG_DOWNHOLE_PRESSURE"
SOURCE_DAILY_AVG_DOWNHOLE_TEMPERATURE = "AVG_DOWNHOLE_TEMPERATURE"
SOURCE_DAILY_AVG_DP_TUBING = "AVG_DP_TUBING"
SOURCE_DAILY_AVG_ANNULUS_PRESS = "AVG_ANNULUS_PRESS"
SOURCE_DAILY_AVG_CHOKE_SIZE_P = "AVG_CHOKE_SIZE_P"
SOURCE_DAILY_AVG_CHOKE_UOM = "AVG_CHOKE_UOM"
SOURCE_DAILY_AVG_WHP_P = "AVG_WHP_P"
SOURCE_DAILY_AVG_WHT_P = "AVG_WHT_P"
SOURCE_DAILY_DP_CHOKE_SIZE = "DP_CHOKE_SIZE"
SOURCE_DAILY_BORE_OIL_VOL = "BORE_OIL_VOL"
SOURCE_DAILY_BORE_GAS_VOL = "BORE_GAS_VOL"
SOURCE_DAILY_BORE_WAT_VOL = "BORE_WAT_VOL"
SOURCE_DAILY_BORE_WI_VOL = "BORE_WI_VOL"
SOURCE_DAILY_FLOW_KIND = "FLOW_KIND"
SOURCE_DAILY_WELL_TYPE = "WELL_TYPE"

# Monthly production source columns
SOURCE_MONTHLY_WELLBORE_NAME = "Wellbore name"
SOURCE_MONTHLY_NPD_CODE = "NPDCode"
SOURCE_MONTHLY_YEAR = "Year"
SOURCE_MONTHLY_MONTH = "Month"
SOURCE_MONTHLY_ON_STREAM = "On Stream"
SOURCE_MONTHLY_OIL = "Oil"
SOURCE_MONTHLY_GAS = "Gas"
SOURCE_MONTHLY_WATER = "Water"
SOURCE_MONTHLY_GI = "GI"
SOURCE_MONTHLY_WI = "WI"

# Wellbore register snapshot columns (the register's CSV exports)
SOURCE_REGISTER_NAME = "wlbWellboreName"
SOURCE_REGISTER_NPDID = "wlbNpdidWellbore"
SOURCE_REGISTER_FIELD_NAME = "wlbField"
SOURCE_REGISTER_FIELD_CODE = "fldNpdidField"
SOURCE_REGISTER_WELL_TYPE = "wlbWellType"
SOURCE_REGISTER_PURPOSE = "wlbPurpose"
SOURCE_REGISTER_CONTENT = "wlbContent"
SOURCE_REGISTER_COMPLETION_YEAR = "wlbCompletionYear"
SOURCE_REGISTER_PARENT_NAME = "wlbDiskosWellboreParent"


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database file path (relative to project root)
DATABASE_PATH = "database/volve.db"

# Display formatting
SEPARATOR_LINE = "=" * 80

# Source data file path
SOURCE_EXCEL_PATH = "data/production/Volve production data.xlsx"

# Sheet names
SHEET_DAILY = "Daily Production Data"
SHEET_MONTHLY = "Monthly Production Data"

# Wellbore register snapshot in the local raw directory, a plain download of
# the Volve Raw repo at its pin (data/raw/README.md). The file names are the
# ones scripts/raw_repo/volve/register.py gives the exports.
SOURCE_REGISTER_PATHS = (
    "data/raw/volve/register/wellbore_development_all.csv",
    "data/raw/volve/register/wellbore_exploration_all.csv",
)

# NPD field code of Volve: the register rows with it are the Volve Wellbores.
VOLVE_NPD_FIELD_CODE = 3420717
