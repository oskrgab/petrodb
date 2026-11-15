"""The register snapshot command, with the HTTP fetch replaced by a fake."""

import datetime as dt
from pathlib import Path

import pytest

from scripts.raw_repo.volve import __main__ as cli
from scripts.raw_repo.volve import register


def test_fetch_register_writes_both_exports_and_the_download_date(
    tmp_path: Path,
) -> None:
    requested: list[str] = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        table = "development" if "wellbore_development_all" in url else "exploration"
        return f"wlbWellboreName,wlbField\n15/9-F-1,VOLVE\n{table}\n".encode()

    raw_dir = tmp_path / "raw" / "volve"
    register.fetch_register(raw_dir, fetch=fake_fetch, today=dt.date(2026, 11, 15))

    folder = raw_dir / "register"
    assert sorted(p.name for p in folder.iterdir()) == [
        "download_date.txt",
        "wellbore_development_all.csv",
        "wellbore_exploration_all.csv",
    ]
    assert (
        (folder / "wellbore_development_all.csv").read_text().endswith("development\n")
    )
    assert (
        (folder / "wellbore_exploration_all.csv").read_text().endswith("exploration\n")
    )
    assert (folder / "download_date.txt").read_text() == "2026-11-15\n"
    assert len(requested) == 2
    assert all(
        url.startswith("https://factpages.sodir.no/") and "rs:Format=CSV" in url
        for url in requested
    )


def test_fetch_register_defaults_to_the_local_raw_directory() -> None:
    assert (
        cli.LOCAL_RAW_DIR
        == Path(__file__).resolve().parents[2] / "data" / "raw" / "volve"
    )


def _not_a_register_export(url: str) -> bytes:
    return b"<html><body>Service unavailable</body></html>\n"


def test_fetch_register_refuses_a_download_that_is_not_a_register_export(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw" / "volve"
    with pytest.raises(register.RegisterError, match="not a wellbore register CSV export"):
        register.fetch_register(raw_dir, fetch=_not_a_register_export)
    assert not (raw_dir / "register").exists()


def test_fetch_register_command_reports_a_bad_download_without_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetch_register = register.fetch_register
    monkeypatch.setattr(
        register,
        "fetch_register",
        lambda raw_dir: fetch_register(raw_dir, fetch=_not_a_register_export),
    )
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["fetch-register", str(tmp_path / "raw" / "volve")])
    assert str(exit_info.value).startswith("error: ")
    assert "not a wellbore register CSV export" in str(exit_info.value)
