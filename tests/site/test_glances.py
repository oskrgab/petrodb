"""The Glances command: what it publishes must be runnable by a visitor."""

import json
from pathlib import Path

import pytest

from scripts.deploy.retarget_data_urls import CANONICAL_HF_BASE
from scripts.site import glances

SITE_DATA = Path(__file__).resolve().parents[2] / "site" / "data"


def test_public_base_matches_the_deploy_host() -> None:
    # The deploy retargets this host per branch; a different one would be
    # published untouched and point stage visitors at main.
    assert glances.PUBLIC_BASE == CANONICAL_HF_BASE


@pytest.mark.parametrize(
    ("value", "expected"),
    [(277, 300), (46.4, 50), (29.5, 30), (330.3, 400), (569.3, 600), (0, 1), (100, 100)],
)
def test_nice_max_rounds_up_to_a_clean_scale_end(value: float, expected: float) -> None:
    assert glances._nice_max(value) == expected


def test_published_sql_reads_from_the_public_host() -> None:
    glance = glances.GLANCES[0]
    published = glances.run_glance(glance)
    assert str(glances.PARQUET_ROOT) not in published["sql"]
    assert glances.PUBLIC_BASE in published["sql"]
    assert "{base}" not in published["sql"]


def test_every_glance_has_committed_output() -> None:
    for glance in glances.GLANCES:
        path = SITE_DATA / glance.dataset / "glances.json"
        ids = {g["id"] for g in json.loads(path.read_text())}
        assert glance.id in ids, f"run `uv run -m scripts.site.glances` ({glance.id})"


def test_series_line_up_with_their_axis() -> None:
    for path in SITE_DATA.glob("*/glances.json"):
        for glance in json.loads(path.read_text()):
            chart = glance["chart"]
            for series in chart["series"]:
                assert len(series["values"]) == len(chart["x"]["values"]), glance["id"]


@pytest.mark.parametrize(
    ("dataset", "covers"),
    [
        # Facts about the committed data, checked by hand against the parquet.
        ("argentina", "85,417 wells, 2006–2025"),
        ("volve", "7 wells, 2007–2016"),
        ("force_2020", "108 wells"),
    ],
)
def test_covers_is_computed_from_the_data(dataset: str, covers: str) -> None:
    facts = json.loads(glances.build(dataset)["facts.json"])
    assert facts["covers"] == covers


def test_dataset_metadata_carries_no_hand_written_facts() -> None:
    # "covers" and "size" live in the computed facts.json; a copy typed into
    # dataset.json would drift from the data.
    for path in SITE_DATA.glob("*/dataset.json"):
        meta = json.loads(path.read_text())
        assert not {"covers", "size"} & meta.keys(), path
        assert (path.parent / "facts.json").is_file(), path.parent.name


@pytest.mark.parametrize("dataset", ["volve", "force_2020", "argentina"])
def test_committed_output_matches_the_data(dataset: str) -> None:
    if not glances.on_disk(dataset):
        pytest.skip(f"parquet/{dataset} is not on disk, nothing to compare")
    assert glances.stale(dataset) == [], (
        f"committed site/data/{dataset} is stale: "
        f"run `uv run -m scripts.site.glances {dataset}`"
    )


def test_a_changed_committed_file_is_reported_stale(tmp_path: Path) -> None:
    glances.write("volve", out_root=tmp_path)
    assert glances.stale("volve", out_root=tmp_path) == []
    facts = tmp_path / "volve" / "facts.json"
    facts.write_text(facts.read_text().replace("7 wells", "8 wells"))
    (tmp_path / "volve" / "files.json").unlink()
    assert glances.stale("volve", out_root=tmp_path) == ["files.json", "facts.json"]


def test_check_skips_a_dataset_that_is_not_on_disk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(glances, "PARQUET_ROOT", tmp_path)
    assert glances.main(["--check", "volve"]) == 0
    assert "skip volve" in capsys.readouterr().out


def test_multi_parquet_tables_are_listed_from_their_manifest() -> None:
    tables = {t["name"]: t for t in glances.list_files("argentina")}
    monthly = tables["monthly_production"]
    assert monthly["kind"] == "multi"
    assert monthly["manifest"] == "monthly_production/_files.json"
    assert len(monthly["files"]) == 20
    assert monthly["rows"] == sum(f["rows"] for f in monthly["files"])
    assert tables["wells"]["kind"] == "single"
