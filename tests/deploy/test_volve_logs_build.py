"""The deploy workflow builds the Volve log tables and publishes them (issue #75).

The log Parquet is never committed (ADR-0011), and the Hugging Face upload
deletes remote Parquet absent from the checkout. So every deploy must restore
the tables from cache or build them, and check they are there, before that
upload. These tests read the workflow's steps and run their scripts with bash,
as the runner does, with a stub ``hf`` on ``PATH``.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

from scripts.raw_repo.volve.pin import read_pin
from scripts.run_pipeline import volve_logs
from tests.deploy.support import (
    REPO_ROOT,
    env_value,
    run_step,
    step_block,
    workflow_lines,
)
from tests.volve.log_fixtures import build_raw_tree

CACHE_STEP = "Restore the Volve log tables (if the pin and sources are unchanged)"
DOWNLOAD_STEP = "Download the raw files the Volve log pipeline reads"
BUILD_STEP = "Build the Volve log tables"
PRESENT_STEP = "Check the Volve log tables are present"
UPLOAD_STEP = "Upload parquet bytes to Hugging Face"
RAW_REPO = "oskrgab/petrodb-raw-volve"
PIN_FILE = "data/raw/volve.pin"


def _step_names() -> list[str]:
    return [
        line.strip().removeprefix("- name: ")
        for line in workflow_lines()
        if line.startswith("      - name: ")
    ]


def _hashed_globs(block: list[str]) -> list[str]:
    text = "\n".join(block)
    inside = re.search(r"hashFiles\((.*?)\)", text, re.S)
    assert inside, "the cache key hashes no files"
    return re.findall(r"'([^']+)'", inside.group(1))


def _trigger_paths() -> list[str]:
    lines = workflow_lines()
    start = lines.index("    paths:")
    paths = []
    for line in lines[start + 1 :]:
        if not line.startswith("      - "):
            break
        paths.append(line.strip().removeprefix("- ").strip("'\""))
    return paths


def _log_tables() -> list[str]:
    """The job env's VOLVE_LOG_TABLES, one path per line of its block scalar."""
    lines = workflow_lines()
    start = next(
        i for i, line in enumerate(lines) if line.strip() == "VOLVE_LOG_TABLES: |"
    )
    indent = len(lines[start]) - len(lines[start].lstrip())
    tables = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        if line.strip():
            tables.append(line.strip())
    return tables


def _pipeline_sources() -> list[str]:
    """The repo files of every Volve module the pipeline imports, repo-relative."""
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, scripts.run_pipeline.volve_logs\n"
            "for m in list(sys.modules.values()):\n"
            "    f = getattr(m, '__file__', None) or ''\n"
            "    if m.__name__.startswith('scripts.') and 'volve' in m.__name__:\n"
            "        print(f)",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    return sorted(str(Path(f).relative_to(REPO_ROOT)) for f in out)


def _covered(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) for g in globs)


# --- Cache and triggers ------------------------------------------------------


def test_cache_is_keyed_on_the_pin_and_every_pipeline_source() -> None:
    globs = _hashed_globs(step_block(CACHE_STEP))

    assert PIN_FILE in globs
    sources = _pipeline_sources()
    assert "scripts/transform/volve_logs/sources.py" in sources
    assert [s for s in sources if not _covered(s, globs)] == []


def test_cache_holds_exactly_the_log_tables() -> None:
    block = "\n".join(step_block(CACHE_STEP))

    assert "path: ${{ env.VOLVE_LOG_TABLES }}" in block
    assert _log_tables() == [
        "parquet/volve/petrophysical_interpretation.parquet",
        "parquet/volve/log_curves.parquet",
    ]


def test_every_log_table_is_gitignored_and_listed_for_the_cache() -> None:
    # A log table added to the build is gitignored; it must be cached too.
    ignored = [
        line.lstrip("/")
        for line in (REPO_ROOT / ".gitignore").read_text().splitlines()
        if line.startswith("/parquet/volve/") and line.endswith(".parquet")
    ]

    assert sorted(ignored) == sorted(_log_tables())


def test_changing_the_pin_or_a_pipeline_source_triggers_the_workflow() -> None:
    triggers = _trigger_paths()

    assert _covered(PIN_FILE, triggers)
    assert [s for s in _pipeline_sources() if not _covered(s, triggers)] == []


# --- Order: the tables are in place before the upload ---------------------


def test_build_and_presence_check_run_before_the_upload() -> None:
    names = _step_names()

    assert (
        names.index(CACHE_STEP)
        < names.index(DOWNLOAD_STEP)
        < names.index(BUILD_STEP)
        < names.index(PRESENT_STEP)
        < names.index(UPLOAD_STEP)
    )


def test_only_a_cache_miss_downloads_and_builds() -> None:
    for name in (DOWNLOAD_STEP, BUILD_STEP):
        block = "\n".join(step_block(name))
        assert "if: steps.cache-volve-logs.outputs.cache-hit != 'true'" in block

    for name in (PRESENT_STEP, UPLOAD_STEP):
        assert not any(line.strip().startswith("if:") for line in step_block(name))


def test_a_failed_build_stops_the_job_before_the_upload() -> None:
    names = _step_names()
    between = names[names.index(BUILD_STEP) : names.index(UPLOAD_STEP) + 1]

    for name in between:
        block = [line.strip() for line in step_block(name)]
        assert not any(line.startswith("continue-on-error:") for line in block), name
        assert not any(
            "always()" in line or "failure()" in line
            for line in block
            if line.startswith("if:")
        ), name
    build = "\n".join(step_block(BUILD_STEP))
    assert "run: uv run python -m scripts.run_pipeline.volve_logs" in build


def test_the_build_command_exits_non_zero_when_a_pre_publish_check_fails(
    tmp_path: Path,
) -> None:
    raw = build_raw_tree(tmp_path / "raw")
    out = tmp_path / "out"
    out.mkdir()
    # A wells table that lacks every Wellbore: the membership check fails.
    duckdb.sql(
        f"COPY (SELECT * FROM '{REPO_ROOT / 'parquet/volve/wells.parquet'}' LIMIT 0) "
        f"TO '{out / 'wells.parquet'}' (FORMAT parquet)"
    )

    result = subprocess.run(
        [sys.executable, "-m", "scripts.run_pipeline.volve_logs", str(raw), str(out)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "PrePublishCheckError" in result.stderr
    assert not (out / "petrophysical_interpretation.parquet").exists()


# --- The download step -------------------------------------------------------


def _stub_bin(tmp_path: Path) -> Path:
    """``hf`` records its arguments; ``uv run X`` runs X with this Python."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    hf = bin_dir / "hf"
    hf.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$HF_ARGS"\n'
        'printf "%s" "${HF_TOKEN:-}" > "$HF_ARGS.token"\n'
    )
    uv = bin_dir / "uv"
    uv.write_text('#!/usr/bin/env bash\n[[ $1 == run ]] && shift\nexec "$@"\n')
    # A wrapper, not a symlink: a venv's Python finds its packages only when
    # started by its own path.
    python = bin_dir / "python"
    python.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n')
    for stub in (hf, uv, python):
        stub.chmod(0o755)
    return bin_dir


def _run_download(
    tmp_path: Path, token: str | None
) -> tuple[subprocess.CompletedProcess[str], Path]:
    args = tmp_path / "hf-args"
    env = {
        "PATH": f"{_stub_bin(tmp_path)}{os.pathsep}{os.environ['PATH']}",
        "HF_ARGS": str(args),
        "HF_TOKEN": token,
        "RAW_REPO": env_value("RAW_REPO", step_block(DOWNLOAD_STEP)),
    }
    return run_step(DOWNLOAD_STEP, env, cwd=REPO_ROOT), args


def test_download_fetches_exactly_the_listed_files_at_the_pin(tmp_path: Path) -> None:
    result, args = _run_download(tmp_path, token="hf_read")

    assert result.returncode == 0, result.stdout + result.stderr
    argv = args.read_text().splitlines()
    assert argv[:2] == ["download", RAW_REPO]
    files = argv[2 : argv.index("--repo-type")]
    assert files == list(volve_logs.raw_files())
    assert "--include" not in argv
    rest = argv[argv.index("--repo-type") :]
    assert rest[rest.index("--repo-type") + 1] == "dataset"
    assert rest[rest.index("--revision") + 1] == read_pin()
    assert rest[rest.index("--local-dir") + 1] == "data/raw/volve"
    assert Path(f"{args}.token").read_text() == "hf_read"


def test_download_refuses_to_run_without_a_token(tmp_path: Path) -> None:
    result, args = _run_download(tmp_path, token=None)

    assert result.returncode != 0
    assert "token" in result.stdout + result.stderr
    assert not args.exists()


def test_download_step_reads_the_raw_repo_with_a_secret_token() -> None:
    # A read token of its own: the upload token never reaches this step.
    token = env_value("HF_TOKEN", step_block(DOWNLOAD_STEP))

    assert token == "${{ secrets.HF_RAW_READ_TOKEN }}"


# --- The presence check ------------------------------------------------------


def _run_present(cwd: Path) -> subprocess.CompletedProcess[str]:
    tables = "\n".join(_log_tables()) + "\n"
    return run_step(PRESENT_STEP, {"VOLVE_LOG_TABLES": tables}, cwd=cwd)


def test_presence_check_passes_when_every_log_table_is_there(tmp_path: Path) -> None:
    for table in _log_tables():
        (tmp_path / table).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / table).write_bytes(b"PAR1")

    result = _run_present(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_presence_check_fails_naming_a_missing_or_empty_table(tmp_path: Path) -> None:
    table = _log_tables()[0]
    (tmp_path / table).parent.mkdir(parents=True)
    (tmp_path / table).write_bytes(b"")

    result = _run_present(tmp_path)

    assert result.returncode != 0
    assert table in result.stdout

    shutil.rmtree(tmp_path / "parquet")
    assert _run_present(tmp_path).returncode != 0


def test_presence_check_fails_when_no_table_is_listed(tmp_path: Path) -> None:
    result = run_step(PRESENT_STEP, {"VOLVE_LOG_TABLES": ""}, cwd=tmp_path)

    assert result.returncode != 0
