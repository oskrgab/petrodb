"""The Volve log pipeline: a local raw directory in, checked log tables out.

``run`` is the one entry point; the command line (``__main__``), the tests and
CI all call it. It reads a raw directory, a plain download of the Raw repo
``oskrgab/petrodb-raw-volve`` at the pin (``data/raw/README.md``), and writes
into an output directory that already holds the Volve ``wells.parquet``, which
the pre-publish checks join against, and the committed ``schema.json``, which
the written table must match. ``raw_files`` names every file ``run`` reads, as
a path within the Raw repo, so CI downloads only those.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.export.volve_logs import parquet_writer
from scripts.transform.volve_logs import curve_catalog, interpretation_builder
from scripts.transform.volve_logs.sources import raw_files

__all__ = ["OUTPUT_DIR", "RAW_DIR", "raw_files", "run"]

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw" / "volve"
OUTPUT_DIR = REPO_ROOT / "parquet" / "volve"


def run(raw_dir: Path = RAW_DIR, output_dir: Path = OUTPUT_DIR) -> Path:
    """Build ``petrophysical_interpretation.parquet`` and its Curve catalog
    ``log_curves.parquet`` in ``output_dir``; return the table's path."""
    output_dir = Path(output_dir)
    with duckdb.connect() as con:
        expected_rows = interpretation_builder.build(con, Path(raw_dir))
        curve_catalog.build(con, interpretation_builder.TABLE)
        return parquet_writer.write(
            con,
            output_dir,
            output_dir / "wells.parquet",
            output_dir / "schema.json",
            expected_rows,
        )
