"""The pin: the Raw repo commit the Volve log pipeline reads, recorded in one file."""

from pathlib import Path

import pytest

from scripts.raw_repo.volve import pin

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pin_lives_in_one_committed_file() -> None:
    assert pin.PIN_FILE == REPO_ROOT / "data" / "raw" / "volve.pin"
    assert pin.PIN_FILE.is_file()


def test_the_committed_pin_names_a_raw_repo_commit() -> None:
    # The Raw repo is filled (#66): the pipeline and CI read a fixed commit.
    assert pin.read_pin() is not None


def test_an_empty_pin_reads_as_none(tmp_path: Path) -> None:
    path = tmp_path / "volve.pin"
    path.write_text("\n")

    assert pin.read_pin(path) is None


def test_a_pin_is_a_full_commit_hash(tmp_path: Path) -> None:
    path = tmp_path / "volve.pin"
    path.write_text("0123456789abcdef0123456789abcdef01234567\n")

    assert pin.read_pin(path) == "0123456789abcdef0123456789abcdef01234567"


def test_a_pin_that_is_not_a_commit_hash_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "volve.pin"
    path.write_text("main\n")

    with pytest.raises(ValueError, match="main"):
        pin.read_pin(path)
