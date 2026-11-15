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

Each source's interpretation is either a LAS pair or a DLIS pair; the two
formats hold the same kind of files under the same names, bar the extension.

Paths are relative to a local raw directory, a plain download of the Raw repo
``oskrgab/petrodb-raw-volve`` (see ``data/raw/README.md``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LOG_TREE = "Well_logs_pr_WELL"
INTERPRETATION_FOLDER = "05.PETROPHYSICAL INTERPRETATION"
INPUT_FILE = "WLC_PETRO_COMPUTED_INPUT_1"
OUTPUT_FILE = "WLC_PETRO_COMPUTED_OUTPUT_1"
LAS = "LAS"
DLIS = "DLIS"


class SourceFileError(Exception):
    """A log file the pipeline needs is missing or cannot be used."""


@dataclass(frozen=True)
class LogSource:
    """The files of one ``source_wellbore``'s petrophysical interpretation.

    Usually an input and an output file, both in ``file_format`` (``LAS`` or
    ``DLIS``, which is also their extension). ``has_output`` is false for a
    source with an input file only: every Interpreted curve of its rows is
    NULL.
    """

    folder: str
    source_wellbore: str
    npd_wellbore_code: int
    has_output: bool = True
    file_format: str = LAS

    def _path(self, raw_dir: Path, name: str) -> Path:
        return Path(raw_dir) / LOG_TREE / self.folder / INTERPRETATION_FOLDER / name

    def input_path(self, raw_dir: Path) -> Path:
        return self._path(raw_dir, f"{INPUT_FILE}.{self.file_format}")

    def output_path(self, raw_dir: Path) -> Path | None:
        return self.unread_output_path(raw_dir) if self.has_output else None

    def unread_output_path(self, raw_dir: Path) -> Path:
        """Where the output file would be, whether or not this source has one."""
        return self._path(raw_dir, f"{OUTPUT_FILE}.{self.file_format}")


# The sources whose interpretation is LAS, one folder each. Only the
# WLC_PETRO_COMPUTED files are read: the geomodel permeability export beside
# them (geomod09/*_KLOGH_NEW.las) is not. 7078 is 15/9-F-11: the parent of the
# Technical sidetrack F-11 T2, and the Wellbore of the top-hole section.
LAS_SOURCES: tuple[LogSource, ...] = (
    LogSource("15_9-F-1", "15/9-F-1", 7223),
    LogSource("15_9-F-1 A", "15/9-F-1 A", 7224),
    LogSource("15_9-F-1 B", "15/9-F-1 B", 7264),
    LogSource("15_9-F-1 C", "15/9-F-1 C", 7405),
    LogSource("15_9-F-11 A", "15/9-F-11 A", 7079),
    LogSource("15_9-F-11 B", "15/9-F-11 B", 7080),
    LogSource("15_9-F-11 T2", "15/9-F-11 T2", 7078),
    LogSource("15_9-F-11", "15/9-F-11", 7078, has_output=False),
    LogSource("15_9-F-12", "15/9-F-12", 5599),
    LogSource("15_9-F-15 D", "15/9-F-15 D", 7289),
)

# The sources whose interpretation exists only as DLIS: an input and an output
# file each, the geomodel export beside them again not read.
DLIS_SOURCES: tuple[LogSource, ...] = tuple(
    LogSource(folder, name, code, file_format=DLIS)
    for folder, name, code in (
        ("15_9-F-4", "15/9-F-4", 5693),
        ("15_9-F-5", "15/9-F-5", 5769),
        ("15_9-F-10", "15/9-F-10", 6099),
        ("15_9-F-14", "15/9-F-14", 5351),
        ("15_9-F-15", "15/9-F-15", 6184),
        ("15_9-F-15 A", "15/9-F-15 A", 5785),
        ("15_9-F-15 B", "15/9-F-15 B", 6046),
        ("15_9-F-15 C", "15/9-F-15 C", 5794),
    )
)

SOURCES: tuple[LogSource, ...] = LAS_SOURCES + DLIS_SOURCES


def raw_files() -> tuple[str, ...]:
    """Every file the pipeline reads, as a path within the Raw repo.

    Paths use ``/`` and keep upstream names, spaces and ``&`` included. The
    deploy workflow downloads exactly these from the Raw repo at the pin, so a
    source added here is fetched in CI with no change to the workflow. An
    input-only source names no output file: the build only checks that none is
    there.
    """
    root = Path()  # an empty root leaves each path relative to the raw directory
    return tuple(
        path.as_posix()
        for source in SOURCES
        for path in (source.input_path(root), source.output_path(root))
        if path is not None
    )
