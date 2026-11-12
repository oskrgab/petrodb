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
