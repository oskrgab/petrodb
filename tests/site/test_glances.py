"""The Glances command: what it publishes must be runnable by a visitor."""

import json
from datetime import date
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
            if chart["kind"] == "log":
                axis = chart["depth"]["values"]
                series_list = [s for track in chart["tracks"] for s in track["series"]]
            else:
                axis = chart["x"]["values"]
                series_list = chart["series"]
            for series in series_list:
                assert len(series["values"]) == len(axis), glance["id"]


def _glance(dataset: str, glance_id: str) -> glances.Glance:
    return next(g for g in glances.GLANCES if (g.dataset, g.id) == (dataset, glance_id))


def test_volve_field_rates_chart_oil_gas_and_water() -> None:
    # Oil peaks in month 2; water overtakes oil from month 3 for good.
    rows = [
        (date(2008, 1, 1), 100_000.0, 15e6, 0.0),
        (date(2008, 2, 1), 200_000.0, 30e6, 50_000.0),
        (date(2008, 3, 1), 80_000.0, 12e6, 90_000.0),
        (date(2008, 4, 1), 40_000.0, 6e6, 120_000.0),
    ]
    built = _glance("volve", "field-rates").build(rows)
    series = {s["name"]: s for s in built["chart"]["series"]}
    assert set(series) == {"Oil", "Gas", "Water"}
    assert series["Gas"]["tone"] == "gas"
    assert series["Gas"]["values"] == [15, 30, 12, 6]  # million Sm³
    assert "200 thousand Sm³ a month in February 2008" in built["takeaway"]
    assert "From March 2008" in built["takeaway"]
    # 63 million Sm³ of gas over 420 thousand Sm³ of oil.
    assert "150 Sm³ of gas for every Sm³ of oil" in built["takeaway"]


def test_volve_cumulative_oil_ranks_wells_from_the_result() -> None:
    rows = [("A", 5.0, 0.0), ("B", 3.0, 0.0), ("C", 1.5, 0.0), ("D", 0.5, 1.0), ("E", 0.0, 7.3)]
    built = _glance("volve", "cumulative-oil").build(rows)
    chart = built["chart"]
    assert chart["kind"] == "bars"
    assert chart["x"]["values"] == ["A", "B", "C", "D", "E"]
    assert chart["series"][0]["values"] == [5.0, 3.0, 1.5, 0.5, 0.0]
    assert chart["series"][1]["values"] == [0.0, 0.0, 0.0, 1.0, 7.3]
    assert "A and B produced 80% of the field's 10.0 million Sm³ of oil" in built["takeaway"]
    assert "E produced none and injected 7.3 million Sm³ of water" in built["takeaway"]


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
