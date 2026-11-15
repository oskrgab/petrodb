"""Execute an upload plan with the Hugging Face CLI. Not tested: it needs the network.

The plan is staged as a tree of symbolic links laid out at the Raw repo paths,
and ``hf upload`` sends that tree. ``hf upload`` splits a large folder into
several commits and resumes when rerun, so an interrupted upload is finished
by running the same command again.
"""

from __future__ import annotations

import fnmatch
import subprocess
import tempfile
from pathlib import Path

from scripts.raw_repo.volve.upload_plan import UploadPlan

RAW_REPO_ID = "oskrgab/petrodb-raw-volve"


def stage(plan: UploadPlan, stage_dir: Path, include: list[str] | None = None) -> int:
    """Link every planned file (or those matching ``include``) at its target path in an empty ``stage_dir``."""
    count = 0
    for planned in plan.files:
        if include and not any(fnmatch.fnmatchcase(planned.target, g) for g in include):
            continue
        link = stage_dir / planned.target
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(planned.source.resolve())
        count += 1
    return count


def upload(plan: UploadPlan, include: list[str] | None = None) -> None:
    """Stage the plan in a fresh temporary directory and upload it.

    Resuming needs no local state: rerun, and ``hf upload`` skips files the
    Raw repo already has.
    """
    with tempfile.TemporaryDirectory(prefix="petrodb-raw-volve-") as tmp:
        root = Path(tmp)
        count = stage(plan, root, include)
        if count == 0:
            raise SystemExit("error: no planned file matches --include")
        print(f"staged {count} files in {root}; uploading to {RAW_REPO_ID}")
        subprocess.run(
            [
                "hf", "upload", RAW_REPO_ID, str(root), ".",
                "--repo-type", "dataset",
                "--commit-message", f"Upload {count} files from the upload plan",
            ],
            check=True,
        )  # fmt: skip
