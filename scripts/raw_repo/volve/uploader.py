"""Execute an upload plan with the Hugging Face CLI. Not tested: it needs the network.

The plan is staged as a tree of symbolic links laid out at the Raw repo paths,
and ``hf upload`` sends that tree. ``hf upload`` splits a large folder into
several commits and resumes when rerun, so an interrupted upload is finished
by running the same command again.

Before it uploads, it makes sure the Raw repo's ``.gitattributes`` stores the
whole log tree in Xet storage (``XET_RULE``). Without that rule the Hub takes
some small binary files for text (SEG-Y files with no extension, whose headers
read as text) and then refuses the commit that holds them. ``.gitattributes``
is the Hub's own file: it is not in the plan, and the Hub adds lines to it.
"""

from __future__ import annotations

import fnmatch
import subprocess
import tempfile
from pathlib import Path

from scripts.raw_repo.volve.upload_plan import BY_WELLBORE_DIR, UploadPlan

RAW_REPO_ID = "oskrgab/petrodb-raw-volve"
XET_RULE = f"{BY_WELLBORE_DIR}/** filter=lfs diff=lfs merge=lfs -text"


class UploadError(Exception):
    """The upload cannot start."""


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


def ensure_xet_rule() -> None:
    """Add ``XET_RULE`` to the Raw repo's ``.gitattributes`` unless it is there."""
    with tempfile.TemporaryDirectory(prefix="petrodb-raw-volve-attrs-") as tmp:
        subprocess.run(
            [
                "hf", "download", RAW_REPO_ID, ".gitattributes",
                "--repo-type", "dataset", "--local-dir", tmp,
            ],
            check=True, stdout=subprocess.DEVNULL,
        )  # fmt: skip
        attributes = Path(tmp) / ".gitattributes"
        text = attributes.read_text()
        if XET_RULE in text.splitlines():
            return
        attributes.write_text(
            text + ("" if text.endswith("\n") else "\n") + XET_RULE + "\n"
        )
        print(f"adding to .gitattributes: {XET_RULE}")
        subprocess.run(
            [
                "hf", "upload", RAW_REPO_ID, str(attributes), ".gitattributes",
                "--repo-type", "dataset",
                "--commit-message", "Store the log tree in Xet storage",
            ],
            check=True,
        )  # fmt: skip


def upload(plan: UploadPlan, include: list[str] | None = None) -> None:
    """Stage the plan in a fresh temporary directory and upload it.

    Resuming needs no local state: rerun, and ``hf upload`` skips files the
    Raw repo already has.
    """
    with tempfile.TemporaryDirectory(prefix="petrodb-raw-volve-") as tmp:
        root = Path(tmp)
        count = stage(plan, root, include)
        if count == 0:
            raise UploadError("no planned file matches --include")
        ensure_xet_rule()
        print(f"staged {count} files in {root}; uploading to {RAW_REPO_ID}")
        subprocess.run(
            [
                "hf", "upload", RAW_REPO_ID, str(root), ".",
                "--repo-type", "dataset",
                "--commit-message", f"Upload {count} files from the upload plan",
            ],
            check=True,
        )  # fmt: skip
