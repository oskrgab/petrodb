"""Guard the Cloudflare deploy tree before it is published (issues #42, #54).

The deploy tree is the built Landing (``site/build``, ADR-0010). Two things must
hold for it, and for the Hugging Face dataset card that ships beside it:

- every data URL names the deploying branch's Hugging Face base, so nothing
  points at the dev Caddy host or at the *other* branch's resolve base;
- no parquet bytes and no ``_files.json`` manifest are in it: those are served
  from Hugging Face only (ADR-0005).

Usage, from the deploy workflow::

    OTHER_BASE=<the other branch's base> python3 -m scripts.deploy.check_deploy_tree site/build hf/README.md

Pure stdlib, so it runs on the runner's system Python.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from scripts.deploy.retarget_data_urls import DEV_CADDY_HOST

# Data files that belong on Hugging Face and never in the Cloudflare tree.
FORBIDDEN_SUFFIXES = (".parquet",)
FORBIDDEN_NAMES = ("_files.json",)


def _files(paths: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            out.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        elif path.is_file():
            out.append(path)
    return out


def problems(paths: Sequence[Path], other_base: str) -> list[str]:
    """Every reason the given files or trees must not ship, one line each."""
    hosts = [DEV_CADDY_HOST.removeprefix("https://"), other_base.rstrip("/")]
    found: list[str] = []
    for path in _files(paths):
        if path.suffix in FORBIDDEN_SUFFIXES or path.name in FORBIDDEN_NAMES:
            found.append(f"{path}: data file in the deploy tree (ADR-0005)")
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for host in hosts:
            if host and host in text:
                found.append(f"{path}: off-branch data host {host}")
    return found


def main(argv: Sequence[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else list(argv)
    other_base = os.environ.get("OTHER_BASE", "")
    if not other_base:
        print("::error::OTHER_BASE is not set")
        sys.exit(2)
    found = problems([Path(a) for a in args], other_base)
    for line in found:
        print(f"::error::{line}")
    if found:
        sys.exit(1)
    print(f"OK: no data files and no off-branch data host in {' '.join(args)}")


if __name__ == "__main__":
    main()
