"""
Parquet Export Pipeline

This script implements the core logic for exporting Volve production database
tables from SQLite to Parquet format. It handles schema preservation,
compression, atomic write operations, and data integrity validation.

Exported tables:
- wells
- daily_production
- monthly_production
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import Boolean, Integer, MetaData, Table, create_engine

# Using absolute imports from project root
from scripts.transform.constants import (
    DATABASE_PATH,
    SEPARATOR_LINE,
    TABLE_DAILY_PRODUCTION,
    TABLE_MONTHLY_PRODUCTION,
    TABLE_WELLS,
)
from scripts.export.export_constants import (
    DEFAULT_COMPRESSION,
    METADATA_FILE_PATH,
    METADATA_FILE_SIZE_MB,
    METADATA_LAST_UPDATED,
    METADATA_ROWS,
    METADATA_TABLE_NAME,
    PARQUET_EXTENSION,
    PARQUET_OUTPUT_DIR,
    PARQUET_README_NAME,
)
from scripts.export.export_utils import (
    generate_metadata_readme,
    get_file_size_mb,
    validate_row_count,
)


def parquet_dtypes(table: Table) -> Dict[str, str]:
    """
    pandas dtypes that keep a column's SQL type in Parquet.

    SQLite hands pandas a nullable INTEGER column holding NULLs as floats and
    a BOOLEAN column as 0/1 integers; without these they would be published
    as DOUBLE and BIGINT.
    """
    dtypes = {}
    for column in table.columns:
        if isinstance(column.type, Boolean):
            dtypes[column.name] = "boolean"
        elif isinstance(column.type, Integer) and column.nullable:
            dtypes[column.name] = "Int64"
    return dtypes


def export_table_to_parquet(
    table_name: str,
    db_path: str,
    output_dir: Path,
    compression: str = DEFAULT_COMPRESSION,
) -> Dict:
    """
    Export a single SQLite table to a Parquet file.

    Reads the table into a pandas DataFrame, writes to a temporary Parquet file,
    validates the row count, and renames to the final destination on success.

    Args:
        table_name: Name of the SQLite table to export
        db_path: Path to the SQLite database
        output_dir: Directory where the Parquet file will be saved
        compression: Compression codec to use (default: snappy)

    Returns:
        Dictionary containing metadata about the exported file
    """
    print(f"Exporting table: {table_name}...")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define file paths
    file_name = f"{table_name}{PARQUET_EXTENSION}"
    final_path = output_dir / file_name
    temp_path = output_dir / f"{file_name}.tmp"
    
    # Create database engine
    engine = create_engine(f"sqlite:///{db_path}")
    
    try:
        # 1. Read from SQLite
        # Use read_sql_query for better control over date parsing if needed
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", engine)
        df = df.astype(parquet_dtypes(Table(table_name, MetaData(), autoload_with=engine)))
        
        # Ensure date columns are proper datetime objects if they look like dates
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            
        row_count = len(df)
        
        # 2. Write to Parquet (temp file)
        # We use the fastparquet or pyarrow engine (automatically selected by pandas)
        df.to_parquet(temp_path, compression=compression, index=False)
        
        # 3. Validate integrity
        if not validate_row_count(table_name, db_path, temp_path):
            if temp_path.exists():
                temp_path.unlink()
            raise ValueError(f"Data integrity check failed for {table_name}: row count mismatch")
            
        # 4. Success - rename temp to final (atomic operation)
        if final_path.exists():
            final_path.unlink()
        temp_path.rename(final_path)
        
        # 5. Collect metadata
        file_size = get_file_size_mb(final_path)
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"   ✓ Successfully exported {row_count:,} rows → {file_name} ({file_size:.4f} MB)")
        
        return {
            METADATA_TABLE_NAME: table_name,
            METADATA_ROWS: row_count,
            METADATA_FILE_SIZE_MB: file_size,
            METADATA_FILE_PATH: str(final_path),
            METADATA_LAST_UPDATED: last_updated
        }
        
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"   ✗ Error exporting {table_name}: {str(e)}")
        raise


def export_all_tables(
    db_path: str = DATABASE_PATH,
    output_dir: str = PARQUET_OUTPUT_DIR,
    compression: str = DEFAULT_COMPRESSION,
) -> List[Dict]:
    """
    Export all production tables to Parquet.

    Args:
        db_path: Path to the SQLite database
        output_dir: Path to the output directory
        compression: Compression codec to use

    Returns:
        List of metadata dictionaries for each exported table
    """
    tables_to_export = [
        TABLE_WELLS,
        TABLE_DAILY_PRODUCTION,
        TABLE_MONTHLY_PRODUCTION
    ]
    
    out_path = Path(output_dir)
    results = []
    
    print(SEPARATOR_LINE)
    print(f"STARTING PARQUET EXPORT PIPELINE")
    print(f"Database: {db_path}")
    print(f"Output:   {output_dir}/")
    print(f"Codec:    {compression or 'None'}")
    print(SEPARATOR_LINE)
    
    for table in tables_to_export:
        metadata = export_table_to_parquet(table, db_path, out_path, compression)
        results.append(metadata)
        
    print(SEPARATOR_LINE)
    print(f"EXPORT COMPLETED: {len(results)} tables processed")
    print(SEPARATOR_LINE)
    
    return results


def main():
    """
    Main entry point for the Parquet export CLI.
    """
    try:
        # 1. Validate environment
        if not Path(DATABASE_PATH).exists():
            print(f"Error: Database not found at {DATABASE_PATH}")
            print("Please run scripts/transform/load_data.py first.")
            sys.exit(1)
            
        # 2. Create output directory
        out_path = Path(PARQUET_OUTPUT_DIR)
        out_path.mkdir(parents=True, exist_ok=True)
        
        # 3. Execute export
        results = export_all_tables()
        
        # 4. Generate metadata README
        readme_path = out_path / PARQUET_README_NAME
        readme_content = generate_metadata_readme(results, template_path=readme_path)
        
        with open(readme_path, "w") as f:
            f.write(readme_content)
            
        print(f"✓ Metadata README generated at {readme_path}")
        print("\nExport summary:")
        for res in results:
            table = res[METADATA_TABLE_NAME]
            rows = res[METADATA_ROWS]
            size = res[METADATA_FILE_SIZE_MB]
            print(f"  - {table:20}: {rows:8,} rows ({size:8.4f} MB)")
            
    except PermissionError:
        print(f"Error: Permission denied writing to {PARQUET_OUTPUT_DIR}")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
