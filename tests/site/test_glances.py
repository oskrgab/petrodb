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
            if chart["kind"] == "log":
                axis = chart["depth"]["values"]
                series_list = [s for track in chart["tracks"] for s in track["series"]]
            else:
                axis = chart["x"]["values"]
                series_list = chart["series"]
            for series in series_list:
                assert len(series["values"]) == len(axis), glance["id"]


def test_multi_parquet_tables_are_listed_from_their_manifest() -> None:
    tables = {t["name"]: t for t in glances.list_files("argentina")}
    monthly = tables["monthly_production"]
    assert monthly["kind"] == "multi"
    assert monthly["manifest"] == "monthly_production/_files.json"
    assert len(monthly["files"]) == 20
    assert monthly["rows"] == sum(f["rows"] for f in monthly["files"])
    assert tables["wells"]["kind"] == "single"
