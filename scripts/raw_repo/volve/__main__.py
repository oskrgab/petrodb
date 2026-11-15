"""Fill the Volve Raw repo, ``oskrgab/petrodb-raw-volve`` (ADR-0011).

Run from the repo root:

    uv run python -m scripts.raw_repo.volve fetch-register [RAW_DIR]
    uv run python -m scripts.raw_repo.volve plan SOURCE_DIR
    uv run python -m scripts.raw_repo.volve upload SOURCE_DIR [--include GLOB ...]

``fetch-register`` downloads the wellbore register snapshot into
``RAW_DIR/register/`` (default: the local raw directory, ``data/raw/volve``).
``plan`` prints the upload plan and touches no network. ``upload`` executes
the plan with the Hugging Face CLI; rerun it to resume an interrupted upload.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.raw_repo.volve import register, upload_plan, uploader

REPO_ROOT = Path(__file__).resolve().parents[3]
# The local raw directory: a plain download of the Raw repo (data/raw/README.md).
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "volve"


def format_plan(plan: upload_plan.UploadPlan) -> str:
    """One ``source<TAB>target`` line per file, then ``#`` lines for totals and adjustments."""
    lines = [f"{f.source}\t{f.target}" for f in plan.files]
    lines.append(f"# files: {len(plan.files)}")
    lines.append(f"# bytes: {plan.total_size}")
    for adjustment in plan.adjustments:
        count = len(adjustment.paths)
        lines.append(
            f"# adjustment: {adjustment.summary} ({count} file{'' if count == 1 else 's'})"
        )
        lines.extend(f"#   {path}" for path in adjustment.paths)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.raw_repo.volve",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    register_cmd = commands.add_parser(
        "fetch-register",
        help="download the wellbore register snapshot into RAW_DIR/register/",
    )
    register_cmd.add_argument("raw_dir", type=Path, nargs="?", default=DEFAULT_RAW_DIR)

    plan_cmd = commands.add_parser("plan", help="print the upload plan, offline")
    plan_cmd.add_argument("source_dir", type=Path)

    upload_cmd = commands.add_parser(
        "upload", help="execute the upload plan with the hf CLI"
    )
    upload_cmd.add_argument("source_dir", type=Path)
    upload_cmd.add_argument(
        "--include",
        action="append",
        metavar="GLOB",
        help="upload only planned files whose Raw repo path matches (repeatable); for a trial run",
    )

    args = parser.parse_args(argv)
    if args.command == "fetch-register":
        folder = register.fetch_register(args.raw_dir)
        print(f"register snapshot written to {folder}")
        return

    try:
        plan = upload_plan.build_plan(args.source_dir)
    except upload_plan.PlanError as err:
        sys.exit(f"error: {err}")

    if args.command == "plan":
        print(format_plan(plan))
    elif args.command == "upload":
        uploader.upload(plan, include=args.include)


if __name__ == "__main__":
    main()
