"""Quoting for names and paths spliced into DuckDB SQL."""

from __future__ import annotations

from pathlib import Path


def identifier(name: str) -> str:
    """``name`` as a quoted SQL identifier, case kept: a mnemonic stays verbatim."""
    return '"' + name.replace('"', '""') + '"'


def path_literal(path: Path) -> str:
    """``path`` as a quoted SQL string literal."""
    return "'" + str(path).replace("'", "''") + "'"
