"""The upload plan for the Volve Raw repo, built offline from a fixture directory.

The fixture is laid out like a local copy of the operator's release: the
by-wellbore log tree under ``Well_logs_pr_WELL/``, the few by-type files under
``Well_logs/``. The register snapshot comes from the local raw directory,
which ``fetch-register`` fills, so the release copy stays read-only. The upload
itself is not tested (issue #65).
"""

import socket
from pathlib import Path

import pytest

from scripts.raw_repo.volve import __main__ as cli
from scripts.raw_repo.volve import upload_plan

REPO_ROOT = Path(__file__).resolve().parents[2]

# Files of the by-wellbore tree that go up as they are. The names carry the
# spaces, ampersands, dots and non-ASCII letters the real tree has.
KEPT = [
    "Well_logs_pr_WELL/15_9-19 B&BT2/05.PETROPHYSICAL INTERPRETATION/15_9-19 BT2_CPI.las",
    "Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/15919bt2.xls",
    "Well_logs_pr_WELL/15_9-19 S&SR/14.DIV.REPORTS/Core Photos on NPD pages.url",
    "Well_logs_pr_WELL/15_9-F-11 T2/05.PETROPHYSICAL INTERPRETATION/F-11 T2 input.LAS",
    "Well_logs_pr_WELL/15_9-F-4/02.LWD_EWL/Run4 Processed Data/R20101.LOG",
    "Well_logs_pr_WELL/15_9-F-4/05.PETROPHYSICAL INTERPRETATION/Sleipner Øst_Hugin.dlis",
    "Well_logs_pr_WELL/VOLVE_INVENTORY.xlsx",
]

# Operating-system junk inside the by-wellbore tree.
JUNK = [
    "Well_logs_pr_WELL/15_9-19 A/12.BIOSTRAT/Thumbs.db",
    "Well_logs_pr_WELL/15_9-19 S&SR/02.LWD_EWL/thumbs.db",
    "Well_logs_pr_WELL/15_9-F-4/.DS_Store",
    "Well_logs_pr_WELL/15_9-F-4/02.LWD_EWL/desktop.ini",
    "Well_logs_pr_WELL/15_9-F-4/02.LWD_EWL/._R20101.LOG",
    "Well_logs_pr_WELL/15_9-F-4/05.PETROPHYSICAL INTERPRETATION/~$report.doc",
]

# The five biostratigraphy files that exist only in the by-type tree, and the
# by-wellbore path each one gets.
BIOSTRAT_ADDED = {
    f"Well_logs/12.BIOSTRAT/15_9-19 B&BT2/{name}": f"Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/{name}"
    for name in ["001.tif", "002.tif", "003.tif", "004.tif", "15-9-19b-bio.pdf"]
}

# The rest of the by-type tree, which duplicates the by-wellbore tree.
BY_TYPE_LEFT_OUT = [
    "Well_logs/04.COMPOSITE/15_9-F-12/list",
    "Well_logs/05.PETROPHYSICAL INTERPRETATION/~$05_Sleipner _Øst_Hugin_Petrophysical_evaluation.doc",
    "Well_logs/05.PETROPHYSICAL INTERPRETATION/15_9-F-4/F-4 CPI.dlis",
]

REGISTER = [
    "register/wellbore_development_all.csv",
    "register/wellbore_exploration_all.csv",
    "register/download_date.txt",
]


def _write(root: Path, relpath: str, content: bytes | None = None) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if content is not None else relpath.encode())


@pytest.fixture
def release(tmp_path: Path) -> Path:
    root = tmp_path / "volve-release"
    for relpath in [*KEPT, *JUNK, *BIOSTRAT_ADDED, *BY_TYPE_LEFT_OUT]:
        _write(root, relpath)
    return root


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    root = tmp_path / "raw" / "volve"
    for relpath in REGISTER:
        _write(root, relpath)
    return root


def _targets(plan: upload_plan.UploadPlan) -> dict[str, Path]:
    return {f.target: f.source for f in plan.files}


def test_by_wellbore_files_keep_their_upstream_paths(
    release: Path, raw_dir: Path
) -> None:
    targets = _targets(upload_plan.build_plan(release, raw_dir))

    for relpath in KEPT:
        assert targets[relpath] == release / relpath


def test_operating_system_junk_is_left_out(release: Path, raw_dir: Path) -> None:
    targets = _targets(upload_plan.build_plan(release, raw_dir))

    for relpath in JUNK:
        assert relpath not in targets


def test_five_biostratigraphy_files_are_added_at_their_by_wellbore_paths(
    release: Path,
    raw_dir: Path,
) -> None:
    targets = _targets(upload_plan.build_plan(release, raw_dir))

    for source, target in BIOSTRAT_ADDED.items():
        assert targets[target] == release / source


def test_rest_of_the_by_type_tree_is_left_out(release: Path, raw_dir: Path) -> None:
    plan = upload_plan.build_plan(release, raw_dir)

    sources = {f.source for f in plan.files}
    for relpath in BY_TYPE_LEFT_OUT:
        assert release / relpath not in sources
    assert not [f.target for f in plan.files if f.target.startswith("Well_logs/")]


def test_a_missing_biostratigraphy_file_stops_the_plan(
    release: Path, raw_dir: Path
) -> None:
    (release / "Well_logs/12.BIOSTRAT/15_9-19 B&BT2/003.tif").unlink()

    with pytest.raises(upload_plan.PlanError, match="003.tif"):
        upload_plan.build_plan(release, raw_dir)


def test_register_snapshot_goes_in_its_own_top_level_folder(
    release: Path, raw_dir: Path
) -> None:
    targets = _targets(upload_plan.build_plan(release, raw_dir))

    for relpath in REGISTER:
        assert targets[relpath] == raw_dir / relpath


def test_a_missing_register_export_stops_the_plan(release: Path, raw_dir: Path) -> None:
    (raw_dir / "register/wellbore_exploration_all.csv").unlink()

    with pytest.raises(upload_plan.PlanError, match="wellbore_exploration_all.csv"):
        upload_plan.build_plan(release, raw_dir)


def test_raw_repo_readme_and_licence_notes_come_from_this_repo(
    release: Path, raw_dir: Path
) -> None:
    targets = _targets(upload_plan.build_plan(release, raw_dir))

    docs = REPO_ROOT / "hf" / "petrodb-raw-volve"
    assert targets["README.md"] == docs / "README.md"
    assert targets["LICENSE.md"] == docs / "LICENSE.md"
    assert targets["register/LICENSE.md"] == docs / "register" / "LICENSE.md"


def test_plan_holds_exactly_the_planned_files_and_renames_nothing_else(
    release: Path,
    raw_dir: Path,
) -> None:
    plan = upload_plan.build_plan(release, raw_dir)

    assert sorted(f.target for f in plan.files) == sorted(
        [
            *KEPT,
            *BIOSTRAT_ADDED.values(),
            *REGISTER,
            "README.md",
            "LICENSE.md",
            "register/LICENSE.md",
        ]
    )
    renamed = {
        f.target
        for f in plan.files
        if f.source.is_relative_to(release) and f.source != release / f.target
    }
    assert renamed == set(BIOSTRAT_ADDED.values())
    assert all(f.size == f.source.stat().st_size for f in plan.files)


def test_plan_reports_each_adjustment_to_upstream(release: Path, raw_dir: Path) -> None:
    adjustments = {
        a.kind: a for a in upload_plan.build_plan(release, raw_dir).adjustments
    }

    assert set(adjustments) == {
        "junk_left_out",
        "added_from_by_type",
        "by_type_left_out",
    }
    assert sorted(adjustments["junk_left_out"].paths) == sorted(
        [
            *JUNK,
            "Well_logs/05.PETROPHYSICAL INTERPRETATION/~$05_Sleipner _Øst_Hugin_Petrophysical_evaluation.doc",
        ]
    )
    assert sorted(adjustments["added_from_by_type"].paths) == sorted(
        BIOSTRAT_ADDED.values()
    )
    assert sorted(adjustments["by_type_left_out"].paths) == sorted(
        [
            "Well_logs/04.COMPOSITE/15_9-F-12/list",
            "Well_logs/05.PETROPHYSICAL INTERPRETATION/15_9-F-4/F-4 CPI.dlis",
        ]
    )
    assert all(a.summary for a in adjustments.values())


def test_plan_command_prints_sources_targets_and_adjustments_offline(
    release: Path,
    raw_dir: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("the plan command opened a network connection")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)

    cli.main(["plan", str(release), "--raw-dir", str(raw_dir)])

    lines = capsys.readouterr().out.splitlines()
    rows = {tuple(line.split("\t")) for line in lines if not line.startswith("#")}
    added = "Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/001.tif"
    assert (str(release / KEPT[0]), KEPT[0]) in rows
    assert (str(release / "Well_logs/12.BIOSTRAT/15_9-19 B&BT2/001.tif"), added) in rows
    assert len(rows) == len(KEPT) + len(BIOSTRAT_ADDED) + len(REGISTER) + 3
    assert f"# files: {len(rows)}" in lines
    assert f"# files from the release: {len(KEPT) + len(BIOSTRAT_ADDED)}" in lines
    assert f"#   {JUNK[0]}" in lines
    assert f"#   {added}" in lines
