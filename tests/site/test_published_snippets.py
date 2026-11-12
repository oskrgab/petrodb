"""Every snippet a Dataset page shows runs against the published files.

These read from Hugging Face, so they run only when asked:

    PETRODB_NETWORK=1 uv run pytest tests/site/test_published_snippets.py
"""

import json
import os
from pathlib import Path

import duckdb
import pytest

from scripts.site.glances import PUBLIC_BASE

SITE_DATA = Path(__file__).resolve().parents[2] / "site" / "data"

pytestmark = pytest.mark.skipif(
    os.environ.get("PETRODB_NETWORK") != "1",
    reason="reads the published files; set PETRODB_NETWORK=1",
)

# Datasets whose page is built from the shared template and whose snippets
# have been checked against the published host.
CHECKED = ["force_2020"]


def _snippets(dataset: str) -> list[tuple[str, str, str]]:
    """(id, language, code) for every query and Glance on the page."""
    meta = json.loads((SITE_DATA / dataset / "dataset.json").read_text())
    glances = json.loads((SITE_DATA / dataset / "glances.json").read_text())
    out = []
    for item in meta.get("queries", []) + glances:
        for lang in ("sql", "python", "polars"):
            if item.get(lang):
                out.append((f"{dataset}/{item['id']}/{lang}", lang, item[lang].replace("{base}", PUBLIC_BASE)))
    return out


CASES = [case for dataset in CHECKED for case in _snippets(dataset)]


@pytest.mark.parametrize(("lang", "code"), [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_snippet_runs_and_returns_rows(lang: str, code: str) -> None:
    if lang == "sql":
        # The page's Python tab wraps the same SQL in duckdb.sql(), which is what runs here.
        rows = duckdb.sql(code.rstrip().rstrip(";")).fetchall()
        assert rows
        return
    namespace: dict = {}
    exec(compile(code, "<snippet>", "exec"), namespace)
    frames = [v for k, v in namespace.items() if hasattr(v, "shape") and not k.startswith("_")]
    assert frames and all(f.shape[0] > 0 for f in frames)
