"""Build the Volve log tables from a local raw directory.

From the repo root, after downloading the Raw repo (``data/raw/README.md``):

    uv run python -m scripts.run_pipeline.volve_logs [RAW_DIR] [OUTPUT_DIR]

``RAW_DIR`` defaults to ``data/raw/volve`` and ``OUTPUT_DIR`` to
``parquet/volve``, which must hold ``wells.parquet``. With
``--list-raw-files`` it builds nothing and prints, one per line, every file it
would read, as a path within the Raw repo; the deploy workflow downloads those.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.run_pipeline.volve_logs import OUTPUT_DIR, RAW_DIR, raw_files, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.run_pipeline.volve_logs")
    parser.add_argument("raw_dir", nargs="?", type=Path, default=RAW_DIR)
    parser.add_argument("output_dir", nargs="?", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--list-raw-files",
        action="store_true",
        help="print the files the build reads, within the Raw repo, and exit",
    )
    args = parser.parse_args(argv)
    if args.list_raw_files:
        print("\n".join(raw_files()))
        return 0
    path = run(raw_dir=args.raw_dir, output_dir=args.output_dir)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
