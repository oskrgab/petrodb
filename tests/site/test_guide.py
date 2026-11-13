"""The "Query the data" guide: what it teaches, in what order, and that it runs."""

import json
import re
from pathlib import Path

import duckdb
import pytest

from tests.site.support import assert_returns_rows, needs_network, run, variants

SITE = Path(__file__).resolve().parents[2] / "site"
GUIDE = SITE / "data" / "guide.json"
GUIDE_PAGE = SITE / "src" / "routes" / "query" / "+page.svelte"


def load_steps() -> list[dict]:
    return json.loads(GUIDE.read_text())["steps"]


def test_steps_follow_the_order_the_guide_teaches() -> None:
    assert [s["id"] for s in load_steps()] == ["one-file", "manifest", "filter", "pin", "download"]


def test_each_step_has_every_variant_or_says_why_not() -> None:
    # Python is derived from the SQL when a step gives none, so SQL and Polars
    # are the variants a step can lack.
    for step in load_steps():
        for lang in ("sql", "polars"):
            assert step.get(lang) or step.get("missing", {}).get(lang), (step["id"], lang)


def test_the_guide_leaves_out_the_lake() -> None:
    # ADR-0008 is not accepted; the guide must not teach ATTACH or the Lake.
    for text in (GUIDE.read_text(), GUIDE_PAGE.read_text()):
        assert "ATTACH" not in text.upper()
        assert not re.search(r"\blake\b", text, re.IGNORECASE)


def test_snippets_take_their_host_from_the_site_data_base() -> None:
    for step in load_steps():
        for lang in ("sql", "python", "polars"):
            code = step.get(lang, "")
            assert "huggingface.co" not in code, (step["id"], lang)
            assert "ocortez.com" not in code, (step["id"], lang)


@needs_network
@pytest.mark.parametrize("step", load_steps(), ids=lambda s: s["id"])
def test_every_snippet_runs_against_the_published_files(
    step: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # the download step writes files
    for lang, code in variants(step):
        if step["id"] == "download":
            run(lang, code)  # writes files and returns no table
        else:
            assert_returns_rows(lang, code)
    if step["id"] == "download":
        assert len(list((tmp_path / "force_2020" / "wells").glob("*.parquet"))) == 108
        assert duckdb.sql("SELECT count(*) FROM 'force_2020_wells.parquet'").fetchone()[0] == 1307297
