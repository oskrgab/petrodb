"""The Glances command: what it publishes must be runnable by a visitor."""

import json
import re
from datetime import date
from pathlib import Path

import pytest

from scripts.deploy.retarget_data_urls import CANONICAL_HF_BASE
from scripts.site import glances
from tests.site.support import find_glance

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DATA = REPO_ROOT / "site" / "data"


def test_public_base_matches_the_deploy_host() -> None:
    # The deploy retargets this host per branch; a different one would be
    # published untouched and point stage visitors at main. The site build
    # rewrites the same host to its own BASE_URL, so its copy must match too.
    assert glances.PUBLIC_BASE == CANONICAL_HF_BASE
    loader = (REPO_ROOT / "site" / "src" / "lib" / "server" / "datasets.ts").read_text()
    site_base = re.search(r'^const CANONICAL_BASE = "([^"]+)";$', loader, re.MULTILINE)
    assert site_base, "datasets.ts no longer declares CANONICAL_BASE"
    assert site_base[1] == CANONICAL_HF_BASE


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


def test_volve_field_rates_chart_oil_gas_and_water() -> None:
    # Oil peaks in month 2; water overtakes oil from month 3 for good.
    rows = [
        (date(2008, 1, 1), 100_000.0, 15e6, 0.0),
        (date(2008, 2, 1), 200_000.0, 30e6, 50_000.0),
        (date(2008, 3, 1), 80_000.0, 12e6, 90_000.0),
        (date(2008, 4, 1), 40_000.0, 6e6, 120_000.0),
    ]
    built = find_glance("volve", "field-rates").build(rows)
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
    built = find_glance("volve", "cumulative-oil").build(rows)
    chart = built["chart"]
    assert chart["kind"] == "bars"
    assert chart["x"]["values"] == ["A", "B", "C", "D", "E"]
    assert chart["series"][0]["values"] == [5.0, 3.0, 1.5, 0.5, 0.0]
    assert chart["series"][1]["values"] == [0.0, 0.0, 0.0, 1.0, 7.3]
    assert "A and B produced 80% of the field's 10.0 million Sm³ of oil" in built["takeaway"]
    assert "E produced none and injected 7.3 million Sm³ of water" in built["takeaway"]


def test_force_lithology_mix_counts_the_wells_from_the_manifest() -> None:
    # The last column is the Manifest's length: one file per well.
    rows = [("Shale", 70.0, 40, 50), ("Sandstone", 29.5, 30, 50), ("Coal", 0.5, 2, 50)]
    built = find_glance("force_2020", "lithology-mix").build(rows)
    assert "appears in 40 of the 50 wells" in built["takeaway"]
    wells = built["chart"]["series"][1]
    assert (wells["unit"], wells["max"], wells["values"]) == ("of 50", 50, [40, 30, 2])


def test_force_log_steps_by_the_constant_the_intervals_assume() -> None:
    step = glances.FORCE_LOG_STEP_M
    assert f"floor(DEPTH_MD / {step}) * {step}" in glances.FORCE_LOG_SQL


def test_force_facts_resolve_wells_through_the_shared_manifest_query() -> None:
    assert glances.FORCE_FACTS_SQL.startswith(glances.FORCE_MANIFEST_SQL)


def test_lookups_are_written_beside_the_glances(monkeypatch: pytest.MonkeyPatch) -> None:
    # A Dataset's extra committed files come from the same registry shape as
    # its Glances and facts, not from a special case in build().
    assert [(lk.dataset, lk.name) for lk in glances.LOOKUPS] == [("petrobras_3w", "event_classes.json")]
    monkeypatch.setattr(glances, "LOOKUPS", [
        glances.Lookup("volve", "first_well.json",
                       "SELECT min(wellbore_name) FROM '{base}/volve/wells.parquet'",
                       lambda rows: {"well": rows[0][0]}),
    ])
    assert json.loads(glances.build("volve")["first_well.json"]) == {"well": "15/9-F-1"}


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


def _computed_numbers(covers: str, years: bool = True) -> set[str]:
    """The counts in a computed "Covers" text, and its years when asked."""
    out = set(re.findall(r"([\d,]+) [A-Za-z]", covers))
    if years:
        for first, last in re.findall(r"(\d{4})–(\d{4})", covers):
            out |= {first, last}
    return out


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"(?<![\w=])\d[\d,]*\b", text))


@pytest.mark.parametrize("dataset", sorted(p.name for p in SITE_DATA.iterdir() if p.is_dir()))
def test_dataset_prose_retypes_no_computed_fact(dataset: str) -> None:
    # #58: no row count, well count or date range on the Landing is hand-written.
    # Prose that repeats one would drift from facts.json when the data changes.
    meta = json.loads((SITE_DATA / dataset / "dataset.json").read_text())
    covers = json.loads((SITE_DATA / dataset / "facts.json").read_text())["covers"]
    prose = " ".join([meta["holds"], meta["grain"], *meta.get("about", [])])
    assert not _computed_numbers(covers) & _numbers(prose)


def test_guide_prose_retypes_no_computed_count() -> None:
    counts = set().union(*(
        _computed_numbers(json.loads(p.read_text())["covers"], years=False)
        for p in SITE_DATA.glob("*/facts.json")
    ))
    guide = json.loads((SITE_DATA / "guide.json").read_text())
    prose = " ".join(guide["intro"] + [line for s in guide["steps"] for line in s["body"]])
    assert not counts & _numbers(prose)


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


def _committed(dataset: str, glance_id: str) -> dict:
    path = SITE_DATA / dataset / "glances.json"
    return next(g for g in json.loads(path.read_text()) if g["id"] == glance_id)


def test_3w_instances_per_event_class_split_by_well_kind() -> None:
    # Pinned release v.1.70.0 / dataset 2.0.0: 2,228 Instances, 594 of them
    # Normal Operation from real wells, 439 simulated Rapid Productivity Loss.
    chart = _committed("petrobras_3w", "instances-by-class")["chart"]
    kinds = {s["name"]: s["values"] for s in chart["series"]}
    assert set(kinds) == {"Real", "Simulated", "Drawn"}
    assert sum(sum(v) for v in kinds.values()) == 2228
    classes = chart["x"]["values"]
    assert len(classes) == 10
    assert kinds["Real"][classes.index("Normal Operation")] == 594
    assert kinds["Simulated"][classes.index("Rapid Productivity Loss")] == 439


def test_3w_hydrate_trace_marks_the_labelled_span() -> None:
    # The Instance is labelled transient (108) from 10:56 on 31 Aug 2011 and
    # steady (8) from 10:46 on 1 Sep until it ends at 13:10.
    chart = _committed("petrobras_3w", "hydrate-pressure")["chart"]
    times = chart["x"]["values"]
    spans = {s["name"]: (times[s["from"]], times[s["to"]]) for s in chart["spans"]}
    assert spans == {
        "Transient": ("2011-08-31T10:50:00", "2011-09-01T10:40:00"),
        "Steady": ("2011-09-01T10:50:00", "2011-09-01T13:10:00"),
    }


def test_3w_event_classes_are_committed_for_the_instance_browser() -> None:
    names = json.loads((SITE_DATA / "petrobras_3w" / "event_classes.json").read_text())
    assert [c["event_class"] for c in names] == list(range(10))
    assert names[8]["description"] == "Hydrate in Production Line"


def test_multi_parquet_tables_are_listed_from_their_manifest() -> None:
    tables = {t["name"]: t for t in glances.list_files("argentina")}
    monthly = tables["monthly_production"]
    assert monthly["kind"] == "multi"
    assert monthly["manifest"] == "monthly_production/_files.json"
    assert len(monthly["files"]) == 20
    assert monthly["rows"] == sum(f["rows"] for f in monthly["files"])
    assert tables["wells"]["kind"] == "single"
