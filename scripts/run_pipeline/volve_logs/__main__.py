"""Build the Volve log tables from a local raw directory.

From the repo root, after downloading the Raw repo (``data/raw/README.md``):

    uv run python -m scripts.run_pipeline.volve_logs [RAW_DIR] [OUTPUT_DIR]

``RAW_DIR`` defaults to ``data/raw/volve`` and ``OUTPUT_DIR`` to
``parquet/volve``, which must hold ``wells.parquet`` and ``schema.json``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.run_pipeline.volve_logs import OUTPUT_DIR, RAW_DIR, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.run_pipeline.volve_logs")
    parser.add_argument("raw_dir", nargs="?", type=Path, default=RAW_DIR)
    parser.add_argument("output_dir", nargs="?", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    path = run(raw_dir=args.raw_dir, output_dir=args.output_dir)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
