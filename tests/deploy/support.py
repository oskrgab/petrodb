"""Shared by the deploy guard tests: read a workflow step and run its script.

The guards live as ``run: |`` blocks in the deploy workflow. ``step_script``
takes one out, read without a YAML parser, and ``run_step`` runs it with bash
the way the runner does.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloudflare-pages.yml"

# The host the Landing is published at, as the deploy job's env sets it.
LANDING = "https://petrodb.ocortez.com"


def workflow_lines() -> list[str]:
    return WORKFLOW.read_text().splitlines()


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def step_block(name: str) -> list[str]:
    """The lines of the step named ``name``, up to the next step or the end."""
    lines = workflow_lines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {name}")
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip() and _indent(line) <= _indent(lines[start]):
            break
        block.append(line)
    return block


def step_script(name: str) -> str:
    """The ``run: |`` block of the step named ``name``, dedented."""
    block = step_block(name)
    run = next(i for i, line in enumerate(block) if line.strip() == "run: |")
    body: list[str] = []
    for line in block[run + 1 :]:
        if line.strip() and _indent(line) <= _indent(block[run]):
            break
        body.append(line)
    indent = min(_indent(b) for b in body if b.strip())
    return "\n".join(b[indent:] for b in body) + "\n"


def env_value(key: str, lines: list[str] | None = None) -> str:
    """The value of the first ``key:`` line in ``lines``, unquoted.

    ``lines`` defaults to the whole workflow; pass ``step_block(name)`` to read
    one step's ``env:``.
    """
    for line in workflow_lines() if lines is None else lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            value = stripped.split(":", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            return value
    raise AssertionError(f"{key} is not set in {WORKFLOW.name}")


def run_step(
    name: str,
    env: dict[str, str | None],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the step's script with ``env`` over this process's environment.

    ``PUBLIC_LANDING_URL`` never leaks in from the caller's environment; a
    ``None`` value leaves that variable unset.
    """
    full = {k: v for k, v in os.environ.items() if k != "PUBLIC_LANDING_URL"}
    for key, value in env.items():
        if value is None:
            full.pop(key, None)
        else:
            full[key] = value
    # GitHub runs `run:` blocks as `bash --noprofile --norc -eo pipefail {0}`.
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step_script(name)],
        check=False,
        cwd=cwd,
        env=full,
        capture_output=True,
        text=True,
        timeout=60,
    )
