"""FORCE 2020's Glances: a vertical log strip and the corpus lithology mix."""

import pytest

from scripts.site import glances


def _glance(glance_id: str) -> dict:
    glance = next(g for g in glances.GLANCES if g.dataset == "force_2020" and g.id == glance_id)
    return glances.run_glance(glance)


@pytest.fixture(scope="module")
def strip() -> dict:
    return _glance("log-strip")["chart"]


def test_log_strip_runs_depth_downward(strip: dict) -> None:
    assert strip["kind"] == "log"
    depth = strip["depth"]["values"]
    assert depth == sorted(depth)
    # Well 15/9-13 is logged from about 495 m to 3,272 m.
    assert 490 <= strip["depth"]["min"] <= depth[0] < 500
    assert 3265 <= depth[-1] <= strip["depth"]["max"] <= 3300


def test_log_strip_tracks_gamma_ray_and_density(strip: dict) -> None:
    names = [s["name"] for track in strip["tracks"] for s in track["series"]]
    assert names == ["Gamma ray", "Bulk density"]
    n = len(strip["depth"]["values"])
    for track in strip["tracks"]:
        for series in track["series"]:
            assert len(series["values"]) == n


def test_log_strip_lithology_column_covers_the_well(strip: dict) -> None:
    column = strip["column"]
    intervals = column["intervals"]
    assert intervals[0]["top"] == strip["depth"]["values"][0]
    for upper, lower in zip(intervals, intervals[1:]):
        assert upper["base"] == lower["top"]
        assert upper["key"] != lower["key"], "adjacent runs of one class are merged"
    keys = {c["key"] for c in column["classes"]}
    assert {i["key"] for i in intervals} == keys
    # Shale dominates 15/9-13 (12,547 of 18,270 samples).
    assert {"shale", "sandstone", "limestone"} <= keys


def test_lithology_mix_covers_every_class_in_the_corpus() -> None:
    chart = _glance("lithology-mix")["chart"]
    assert chart["kind"] == "bars"
    # The 12 classes and their sample counts are listed in parquet/force_2020/README.md.
    assert len(chart["x"]["values"]) == 12
    assert chart["x"]["values"][0] == "Shale"
    share, wells = chart["series"]
    assert sum(share["values"]) == pytest.approx(100, abs=0.1)
    assert share["values"][0] == pytest.approx(804_778 / 1_307_297 * 100, abs=0.01)
    assert max(wells["values"]) <= 108
