"""Every snippet a Dataset page shows runs against the published files.

These read from Hugging Face, so they run only when asked:

    PETRODB_NETWORK=1 uv run pytest tests/site/test_published_snippets.py
"""

import json
from pathlib import Path

import pytest

from tests.site.support import assert_returns_rows, needs_network, variants

SITE_DATA = Path(__file__).resolve().parents[2] / "site" / "data"

pytestmark = needs_network


def _snippets(dataset: Path) -> list[tuple[str, str, str]]:
    """(id, language, code) for every query and Glance on a Dataset's page."""
    meta = json.loads((dataset / "dataset.json").read_text())
    glances_path = dataset / "glances.json"
    glances = json.loads(glances_path.read_text()) if glances_path.is_file() else []
    return [
        (f"{dataset.name}/{item['id']}/{lang}", lang, code)
        for item in meta.get("queries", []) + glances
        for lang, code in variants(item)
    ]


CASES = [case for dataset in sorted(SITE_DATA.glob("*/dataset.json")) for case in _snippets(dataset.parent)]


@pytest.mark.parametrize(("lang", "code"), [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_snippet_runs_and_returns_rows(lang: str, code: str) -> None:
    assert_returns_rows(lang, code)
