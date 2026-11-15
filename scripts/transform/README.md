# Data Transformation Scripts

This directory contains scripts for transforming raw Volve production data from Excel format into a structured SQLite database.
The `wells` table also lists the Volve wellbores that never produced, from the wellbore register snapshot in the local raw directory (`data/raw/volve/register/`, see [`data/raw/README.md`](../../data/raw/README.md)).

## Files

### Core Scripts

- **`constants.py`** - Centralized constants and column definitions
  - Database table and column names
  - Source Excel column mappings
  - File paths and configuration
  - Reused across all transformation scripts

- **`create_tables.py`** - Database schema creation using SQLAlchemy Core
  - Defines three tables: wells, daily_production, monthly_production
  - Creates proper relationships and indexes
  - Educational SQL output (echo=True)
  - Run this FIRST to create the database structure

### Documentation

- **`SCHEMA_DOCUMENTATION.md`** - Complete database schema reference
- **`USAGE_EXAMPLES.md`** - SQL query examples and analysis patterns
- **`../explore/PRODUCTION_DATA_FINDINGS.md`** - Source data analysis

## Usage

### 1. Create Database Schema

```bash
# From project root
uv run python scripts/transform/create_tables.py
```

This creates `database/volve.db` with three empty tables:
- `wells` (master/dimension table)
- `daily_production` (time-series fact table)
- `monthly_production` (time-series fact table)

### 2. Load Data

```bash
# From project root; the register snapshot must be in data/raw/volve/register/
uv run python -m scripts.raw_repo.volve fetch-register   # or download it from the Raw repo
uv run python scripts/transform/load_data.py
```

This script loads all data into the database:
1. Joins the wellbores of the production source to the Volve wellbores of the register snapshot → populates `wells` table
2. Transforms daily production data → populates `daily_production` table
3. Cleans and transforms monthly data → populates `monthly_production` table

## Database Schema Overview

The database uses a **star schema** with one dimension table (wells) and two fact tables (daily_production, monthly_production).

For complete schema details, see **[SCHEMA_DOCUMENTATION.md](SCHEMA_DOCUMENTATION.md)**.

## Design Principles

### SQLAlchemy Core (Not ORM)
All scripts use **SQLAlchemy Core** to stay close to raw SQL:
```python
# GOOD: Explicit SQL using Core
from sqlalchemy import text, Table, Column, Integer

query = text("SELECT * FROM wells WHERE npd_wellbore_code = :code")
result = conn.execute(query, {"code": 7405})
```

### Educational Focus
- SQL statements are logged (echo=True)
- Clear comments explaining each step
- Type hints for readability
- Follows project CLAUDE.md guidelines

### Constants-Based Design
Column names defined once in `constants.py`:
```python
from constants import WELLS_NPD_WELLBORE_CODE, DAILY_DATE

# Use constants instead of strings
wells_table.c[WELLS_NPD_WELLBORE_CODE]
```

Benefits:
- Avoid typos
- IDE autocomplete
- Easy refactoring
- Self-documenting code

## Database File Location

**Path**: `database/volve.db`

- Created automatically by `create_tables.py`
- SQLite format (single file)
- Portable and version-controllable
- ~5-10 MB when fully loaded

## Current Status

1. ✅ Schema created (`create_tables.py`)
2. ✅ Data loading implemented (`load_data.py`)
3. ✅ Database populated with 27 wellbores (7 with production), 15,634 daily records, 526 monthly records
4. ✅ SQL query examples available in [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)

## Dependencies

Defined in `pyproject.toml`:
- `sqlalchemy` - Database toolkit (Core only)
- `pandas` - Excel file reading
- `openpyxl` - Excel support for pandas

Install with:
```bash
uv sync
```

## Troubleshooting

### "Table already exists" Error
```bash
# Delete the database and recreate
rm database/volve.db
uv run python scripts/transform/create_tables.py
```

### Import Errors
Make sure you run scripts from project root:
```bash
# ✅ Correct
uv run python scripts/transform/create_tables.py

# ❌ Wrong
cd scripts/transform
uv run python create_tables.py  # Can't find constants.py
```

### SQLite Browser
To inspect the database visually:
- Install [DB Browser for SQLite](https://sqlitebrowser.org/)
- Open `database/volve.db`
- View tables, schema, and run queries

## Educational Notes

This transformation pipeline demonstrates:

1. **Star Schema Design**: Dimension table (wells) + fact tables (production)
2. **Referential Integrity**: Foreign key constraints
3. **Composite Keys**: Multi-column primary keys for time-series
4. **Indexing Strategy**: Date and wellbore indexes for performance
5. **Explicit SQL**: SQLAlchemy Core keeps SQL visible
6. **Constants Pattern**: Centralized definitions reduce errors

Compare to typical ORM approach:
```python
# ORM (hides SQL)
session.query(Well).filter(Well.code == "F-1").all()

# Core (shows SQL)
query = text("SELECT * FROM wells WHERE wellbore_code = :code")
conn.execute(query, {"code": "F-1"})
```

The Core approach is more educational for learning SQL and database concepts.
