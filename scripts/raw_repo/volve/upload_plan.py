"""The upload plan for the Volve Raw repo: every local file and the path it gets there.

The source directory is a local copy of the operator's Volve release, keeping
upstream paths:

- ``Well_logs_pr_WELL/``: the by-wellbore log tree, uploaded whole.
- ``Well_logs/``: the by-type tree, which duplicates the by-wellbore tree. Only
  the five biostratigraphy files missing from the by-wellbore tree are taken.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.raw_repo.volve import RAW_REPO_DOCS_DIR, register

BY_WELLBORE_DIR = "Well_logs_pr_WELL"
BY_TYPE_DIR = "Well_logs"

# Files an operating system or an office suite leaves behind, not upstream data:
# thumbnail caches, folder metadata and lock files of open documents.
JUNK_NAMES = {"thumbs.db", "desktop.ini", ".ds_store"}
JUNK_PREFIXES = ("~$", "._")


def is_junk(path: Path) -> bool:
    return path.name.lower() in JUNK_NAMES or path.name.startswith(JUNK_PREFIXES)


# Biostratigraphy files for 15/9-19 B that upstream ships only in the by-type
# tree, and the by-wellbore path each one would have.
_BIOSTRAT_19B = ["001.tif", "002.tif", "003.tif", "004.tif", "15-9-19b-bio.pdf"]
BY_TYPE_ADDITIONS = {
    f"{BY_TYPE_DIR}/12.BIOSTRAT/15_9-19 B&BT2/{name}": f"{BY_WELLBORE_DIR}/15_9-19 B&BT2/12.BIOSTRAT/{name}"
    for name in _BIOSTRAT_19B
}


class PlanError(Exception):
    """The source directory cannot be planned as it is."""


@dataclass(frozen=True)
class PlannedFile:
    """One local file and its path in the Raw repo."""

    source: Path
    target: str
    size: int


@dataclass(frozen=True)
class Adjustment:
    """One change the plan makes to the upstream layout, stated in the Raw repo's README."""

    kind: str
    summary: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class UploadPlan:
    source_dir: Path
    files: tuple[PlannedFile, ...]
    adjustments: tuple[Adjustment, ...]

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def release_files(self) -> tuple[PlannedFile, ...]:
        """The planned files read from the release copy, without the register and docs."""
        return tuple(f for f in self.files if f.source.is_relative_to(self.source_dir))


def _planned_file(source: Path, target: str) -> PlannedFile:
    return PlannedFile(source=source, target=target, size=source.stat().st_size)


def _files_under(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file())


def build_plan(source_dir: Path, raw_dir: Path) -> UploadPlan:
    """Plan the upload of ``source_dir`` to the Raw repo. Reads the disk only.

    ``source_dir`` is the local copy of the operator's release and is only read.
    The register snapshot comes from ``raw_dir/register/``, which the
    fetch-register command fills.

    The Raw repo's own README and licence notes come from this repo
    (``RAW_REPO_DOCS_DIR``).
    """
    files: list[PlannedFile] = []
    junk: list[str] = []

    for path in _files_under(source_dir / BY_WELLBORE_DIR):
        relpath = path.relative_to(source_dir).as_posix()
        if is_junk(path):
            junk.append(relpath)
        else:
            files.append(_planned_file(path, relpath))

    by_wellbore_targets = {f.target for f in files}
    for relpath, target in BY_TYPE_ADDITIONS.items():
        source = source_dir / relpath
        if not source.is_file():
            raise PlanError(
                f"by-type file missing from the source directory: {relpath}"
            )
        if target in by_wellbore_targets:
            raise PlanError(
                f"by-type file would overwrite a by-wellbore file: {target}"
            )
        files.append(_planned_file(source, target))

    by_type_left_out: list[str] = []
    for path in _files_under(source_dir / BY_TYPE_DIR):
        relpath = path.relative_to(source_dir).as_posix()
        if relpath in BY_TYPE_ADDITIONS:
            continue
        (junk if is_junk(path) else by_type_left_out).append(relpath)

    for name in register.SNAPSHOT_FILES:
        relpath = f"{register.REGISTER_DIR}/{name}"
        if not (raw_dir / relpath).is_file():
            raise PlanError(
                f"register snapshot file missing: {raw_dir / relpath} "
                "(run the fetch-register command first)"
            )
        files.append(_planned_file(raw_dir / relpath, relpath))

    for path in _files_under(RAW_REPO_DOCS_DIR):
        files.append(
            _planned_file(path, path.relative_to(RAW_REPO_DOCS_DIR).as_posix())
        )

    adjustments = (
        Adjustment(
            kind="junk_left_out",
            summary="Operating-system junk files (thumbnail caches, folder metadata, "
            "office lock files) are left out.",
            paths=tuple(junk),
        ),
        Adjustment(
            kind="added_from_by_type",
            summary="Biostratigraphy files for 15/9-19 B that upstream ships only in its "
            "by-type tree are added at the path they would have in the by-wellbore tree.",
            paths=tuple(BY_TYPE_ADDITIONS.values()),
        ),
        Adjustment(
            kind="by_type_left_out",
            summary=f"The rest of the by-type tree ({BY_TYPE_DIR}/) is left out: "
            "it duplicates the by-wellbore tree.",
            paths=tuple(by_type_left_out),
        ),
    )
    return UploadPlan(
        source_dir=source_dir, files=tuple(files), adjustments=adjustments
    )
