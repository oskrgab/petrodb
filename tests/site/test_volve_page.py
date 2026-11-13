"""Volve's Dataset page: what a visitor copies from it must run and return rows.

Snippets are run against the committed ``parquet/volve`` tree, which is what
the deploy publishes to Hugging Face byte for byte.
"""

import json
from pathlib import Path

import pytest

from scripts.site.glances import PARQUET_ROOT
from tests.site.support import assert_returns_rows, variants

SITE_DATA = Path(__file__).resolve().parents[2] / "site" / "data" / "volve"
LOCAL_BASE = str(PARQUET_ROOT)

META = json.loads((SITE_DATA / "dataset.json").read_text())
GLANCES = json.loads((SITE_DATA / "glances.json").read_text())

CASES = [
    (f"{item['id']}/{lang}", lang, code)
    for item in META["queries"] + GLANCES
    for lang, code in variants(item, base=LOCAL_BASE)
]


def test_volve_is_ready_with_every_page_section_filled() -> None:
    assert META["ready"] is True
    for field in ("about", "units", "queries", "source", "licence"):
        assert META[field], field
    assert META["petroviz"]["url"] == "https://petroviz.ocortez.com/production"


@pytest.mark.parametrize(("lang", "code"), [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_snippet_returns_rows_from_the_committed_tree(lang: str, code: str) -> None:
    assert_returns_rows(lang, code)
