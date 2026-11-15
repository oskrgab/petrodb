"""The pin: the commit of ``oskrgab/petrodb-raw-volve`` that the Volve log pipeline reads.

It has one home, ``data/raw/volve.pin``: a single full commit hash, or nothing
while the Raw repo is not filled yet. The pipeline reads it with
``read_pin``; the deploy workflow reads the same file (``cat``, ``hashFiles``)
for its download revision and its cache key. Moving the pin is a reviewed
change (ADR-0011).
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts.raw_repo.volve import PIN_FILE


_COMMIT = re.compile(r"[0-9a-f]{40}")


def read_pin(path: Path = PIN_FILE) -> str | None:
    """The pinned commit hash, or ``None`` while the pin is empty."""
    value = path.read_text().strip()
    if not value:
        return None
    if not _COMMIT.fullmatch(value):
        raise ValueError(
            f"{path}: the pin must be a full 40-character commit hash, got {value!r}"
        )
    return value
