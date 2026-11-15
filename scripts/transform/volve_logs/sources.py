"""Which raw files the Volve log pipeline reads, and which Wellbore each belongs to.

The Wellbore comes from the upstream folder name, never from a file header:
headers name the same Wellbore in several ways, and some name another. This
mapping is the committed answer. Each source carries the operator's name for
it (``source_wellbore``) and the register's ``npd_wellbore_code``.

Paths are relative to a local raw directory, a plain download of the Raw repo
``oskrgab/petrodb-raw-volve`` (see ``data/raw/README.md``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LOG_TREE = "Well_logs_pr_WELL"
INTERPRETATION_FOLDER = "05.PETROPHYSICAL INTERPRETATION"
INPUT_FILE = "WLC_PETRO_COMPUTED_INPUT_1.LAS"
OUTPUT_FILE = "WLC_PETRO_COMPUTED_OUTPUT_1.LAS"


@dataclass(frozen=True)
class LasPair:
    """The input and output LAS files of one Wellbore's petrophysical interpretation."""

    folder: str
    source_wellbore: str
    npd_wellbore_code: int

    def _path(self, raw_dir: Path, name: str) -> Path:
        return Path(raw_dir) / LOG_TREE / self.folder / INTERPRETATION_FOLDER / name

    def input_path(self, raw_dir: Path) -> Path:
        return self._path(raw_dir, INPUT_FILE)

    def output_path(self, raw_dir: Path) -> Path:
        return self._path(raw_dir, OUTPUT_FILE)


# The Wellbores whose interpretation is a LAS pair in a folder of their own.
# Only the two WLC_PETRO_COMPUTED files are read: the geomodel permeability
# export beside them (geomod09/*_KLOGH_NEW.las) is not.
LAS_PAIRS: tuple[LasPair, ...] = (
    LasPair("15_9-F-1", "15/9-F-1", 7223),
    LasPair("15_9-F-1 A", "15/9-F-1 A", 7224),
    LasPair("15_9-F-1 B", "15/9-F-1 B", 7264),
    LasPair("15_9-F-1 C", "15/9-F-1 C", 7405),
    LasPair("15_9-F-11 A", "15/9-F-11 A", 7079),
    LasPair("15_9-F-11 B", "15/9-F-11 B", 7080),
    LasPair("15_9-F-12", "15/9-F-12", 5599),
    LasPair("15_9-F-15 D", "15/9-F-15 D", 7289),
)


def raw_files() -> tuple[str, ...]:
    """Every file the pipeline reads, as a path within the Raw repo.

    Paths use ``/`` and keep upstream names, spaces and ``&`` included. The
    deploy workflow downloads exactly these from the Raw repo at the pin, so a
    source added here is fetched in CI with no change to the workflow.
    """
    root = Path()  # an empty root leaves each path relative to the raw directory
    return tuple(
        path.as_posix()
        for pair in LAS_PAIRS
        for path in (pair.input_path(root), pair.output_path(root))
    )
