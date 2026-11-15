"""Which raw files the Volve log pipeline reads, and which Wellbore each belongs to.

The Wellbore comes from the upstream folder name, never from a file header:
headers name the same Wellbore in several ways, and some name another. This
mapping is the committed answer. Each source carries the operator's name for
it (``source_wellbore``) and the register's ``npd_wellbore_code``.

A Technical sidetrack (``15/9-F-11 T2``) is not in the register: its rows take
the ``npd_wellbore_code`` of its parent Wellbore and keep the operator's name
in ``source_wellbore``. The 15/9-F-11 top-hole section, an input file with no
output file, is a source of its own: it lies inside the depth range of F-11 T2
but holds different values, so the two are never merged.

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
    """The input and output LAS files of one source's petrophysical interpretation.

    ``has_output`` is false for a source with an input file only: every
    Interpreted curve of its rows is NULL.
    """

    folder: str
    source_wellbore: str
    npd_wellbore_code: int
    has_output: bool = True

    def _path(self, raw_dir: Path, name: str) -> Path:
        return Path(raw_dir) / LOG_TREE / self.folder / INTERPRETATION_FOLDER / name

    def input_path(self, raw_dir: Path) -> Path:
        return self._path(raw_dir, INPUT_FILE)

    def output_path(self, raw_dir: Path) -> Path | None:
        return self._path(raw_dir, OUTPUT_FILE) if self.has_output else None


# The sources whose interpretation is LAS, one folder each. Only the
# WLC_PETRO_COMPUTED files are read: the geomodel permeability export beside
# them (geomod09/*_KLOGH_NEW.las) is not. 7078 is 15/9-F-11: the parent of the
# Technical sidetrack F-11 T2, and the Wellbore of the top-hole section.
LAS_PAIRS: tuple[LasPair, ...] = (
    LasPair("15_9-F-1", "15/9-F-1", 7223),
    LasPair("15_9-F-1 A", "15/9-F-1 A", 7224),
    LasPair("15_9-F-1 B", "15/9-F-1 B", 7264),
    LasPair("15_9-F-1 C", "15/9-F-1 C", 7405),
    LasPair("15_9-F-11 A", "15/9-F-11 A", 7079),
    LasPair("15_9-F-11 B", "15/9-F-11 B", 7080),
    LasPair("15_9-F-11 T2", "15/9-F-11 T2", 7078),
    LasPair("15_9-F-11", "15/9-F-11", 7078, has_output=False),
    LasPair("15_9-F-12", "15/9-F-12", 5599),
    LasPair("15_9-F-15 D", "15/9-F-15 D", 7289),
)
