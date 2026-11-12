"""Volve's Dataset page: what a visitor copies from it must run and return rows.

Snippets are run against the committed ``parquet/volve`` tree, which is what
the deploy publishes to Hugging Face byte for byte.
"""

import json
from pathlib import Path

import duckdb
import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DATA = REPO_ROOT / "site" / "data" / "volve"
LOCAL_BASE = str(REPO_ROOT / "parquet")

META = json.loads((SITE_DATA / "dataset.json").read_text())
GLANCES = json.loads((SITE_DATA / "glances.json").read_text())
PUBLIC_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/main"


def _queries() -> list[dict]:
    return META["queries"]


def test_volve_is_ready_with_every_page_section_filled() -> None:
    assert META["ready"] is True
    for field in ("about", "units", "queries", "source", "licence"):
        assert META[field], field
    assert META["petroviz"]["url"] == "https://petroviz.ocortez.com/production"


@pytest.mark.parametrize("query", _queries(), ids=lambda q: q["id"])
def test_query_sql_returns_rows(query: dict) -> None:
    rows = duckdb.connect().execute(query["sql"].format(base=LOCAL_BASE)).fetchall()
    assert rows


@pytest.mark.parametrize(
    "code",
    [q["polars"] for q in _queries() if "polars" in q]
    + [g["polars"].replace(PUBLIC_BASE, "{base}") for g in GLANCES if "polars" in g],
)
def test_polars_snippet_returns_rows(code: str) -> None:
    scope: dict = {}
    exec(code.replace("{base}", LOCAL_BASE), scope)
    frames = [v for v in scope.values() if isinstance(v, pl.DataFrame)]
    assert frames and all(f.height for f in frames)
