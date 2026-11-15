"""The Volve log pipeline names the raw files it reads, so CI downloads only those.

The deploy workflow fetches exactly this list from the Raw repo at the pin
(issue #75) instead of repeating it. A raw directory holding only the listed
files must build the same table as the full tree.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

from scripts.run_pipeline import volve_logs
from tests.volve.log_fixtures import build_raw_tree

REPO_ROOT = Path(__file__).resolve().parents[2]
WELLS = REPO_ROOT / "parquet" / "volve" / "wells.parquet"
TABLE = "petrophysical_interpretation.parquet"


def _output_dir(path: Path) -> Path:
    path.mkdir()
    shutil.copy(WELLS, path / "wells.parquet")
    return path


def _table(path: Path) -> list[tuple]:
    return duckdb.sql(f"SELECT * FROM '{path}' ORDER BY ALL").fetchall()


def test_raw_files_are_paths_within_the_raw_repo() -> None:
    files = volve_logs.raw_files()

    assert len(files) == 16  # the input and output LAS files of eight Wellbores
    assert len(set(files)) == len(files)
    assert (
        "Well_logs_pr_WELL/15_9-F-1 A/05.PETROPHYSICAL INTERPRETATION/"
        "WLC_PETRO_COMPUTED_INPUT_1.LAS"
    ) in files
    for name in files:
        assert not Path(name).is_absolute()
        assert "\\" not in name and ".." not in Path(name).parts


def test_the_listed_files_alone_build_the_same_table(tmp_path: Path) -> None:
    full = build_raw_tree(tmp_path / "full")
    only_listed = tmp_path / "only_listed"
    for name in volve_logs.raw_files():
        target = only_listed / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(full / name, target)

    from_full = volve_logs.run(raw_dir=full, output_dir=_output_dir(tmp_path / "a"))
    from_listed = volve_logs.run(
        raw_dir=only_listed, output_dir=_output_dir(tmp_path / "b")
    )

    assert _table(from_listed) == _table(from_full)


def test_the_command_line_prints_the_raw_files_one_per_line(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "scripts.run_pipeline.volve_logs", "--list-raw-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == list(volve_logs.raw_files())
