"""Fill the Volve Raw repo, ``oskrgab/petrodb-raw-volve`` (ADR-0011).

Run from the repo root:

    uv run python -m scripts.raw_repo.volve fetch-register [RAW_DIR]
    uv run python -m scripts.raw_repo.volve plan SOURCE_DIR [--raw-dir RAW_DIR]
    uv run python -m scripts.raw_repo.volve upload SOURCE_DIR [--raw-dir RAW_DIR] [--include GLOB ...]

SOURCE_DIR is a local copy of the operator's release, keeping upstream paths;
it is only read. RAW_DIR is the local raw directory (default ``data/raw/volve``).

``fetch-register`` downloads the wellbore register snapshot into
``RAW_DIR/register/``. ``plan`` prints the upload plan (the release files, the
register snapshot from RAW_DIR and the Raw repo docs) and touches no network.
``upload`` executes the plan with the Hugging Face CLI; rerun it to resume an
interrupted upload.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.raw_repo.volve import LOCAL_RAW_DIR, register, upload_plan, uploader


def format_plan(plan: upload_plan.UploadPlan) -> str:
    """One ``source<TAB>target`` line per file, then ``#`` lines for totals and adjustments."""
    lines = [f"{f.source}\t{f.target}" for f in plan.files]
    lines.append(f"# files: {len(plan.files)}")
    lines.append(f"# bytes: {plan.total_size}")
    release = plan.release_files
    lines.append(f"# files from the release: {len(release)}")
    lines.append(f"# bytes from the release: {sum(f.size for f in release)}")
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
    register_cmd.add_argument("raw_dir", type=Path, nargs="?", default=LOCAL_RAW_DIR)

    plan_cmd = commands.add_parser("plan", help="print the upload plan, offline")

    upload_cmd = commands.add_parser(
        "upload", help="execute the upload plan with the hf CLI"
    )
    upload_cmd.add_argument(
        "--include",
        action="append",
        metavar="GLOB",
        help="upload only planned files whose Raw repo path matches (repeatable); for a trial run",
    )

    for cmd in (plan_cmd, upload_cmd):
        cmd.add_argument(
            "source_dir", type=Path, help="local copy of the operator's release"
        )
        cmd.add_argument(
            "--raw-dir",
            type=Path,
            default=LOCAL_RAW_DIR,
            help="local raw directory whose register/ holds the snapshot (default: %(default)s)",
        )

    args = parser.parse_args(argv)
    try:
        if args.command == "fetch-register":
            folder = register.fetch_register(args.raw_dir)
            print(f"register snapshot written to {folder}")
        elif args.command == "plan":
            print(format_plan(upload_plan.build_plan(args.source_dir, args.raw_dir)))
        elif args.command == "upload":
            uploader.upload(
                upload_plan.build_plan(args.source_dir, args.raw_dir),
                include=args.include,
            )
    except (upload_plan.PlanError, register.RegisterError, uploader.UploadError) as err:
        sys.exit(f"error: {err}")


if __name__ == "__main__":
    main()
