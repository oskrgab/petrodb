"""The "Query the data" guide: what it teaches, in what order, and that it runs."""

import json
import os
import re
from pathlib import Path

import duckdb
import pytest

from scripts.site import glances

SITE = Path(__file__).resolve().parents[2] / "site"
GUIDE = SITE / "data" / "guide.json"
GUIDE_PAGE = SITE / "src" / "routes" / "query" / "+page.svelte"

# The repository root that `{repo}` stands for; `{base}` is its `main` revision.
REPO = glances.PUBLIC_BASE.removesuffix("/resolve/main")

# Running the snippets fetches from Hugging Face, so it is opt-in.
NETWORK = os.environ.get("PETRODB_NETWORK") == "1"


def load_steps() -> list[dict]:
    return json.loads(GUIDE.read_text())["steps"]


def fill(code: str) -> str:
    return code.replace("{base}", glances.PUBLIC_BASE).replace("{repo}", REPO)


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


def _variants(step: dict) -> list[tuple[str, str]]:
    sql = fill(step["sql"])
    python = fill(step["python"]) if step.get("python") else None
    out = [("sql", sql), ("python", python)]
    if step.get("polars"):
        out.append(("polars", fill(step["polars"])))
    return out


@pytest.mark.skipif(not NETWORK, reason="set PETRODB_NETWORK=1 to run against the published files")
@pytest.mark.parametrize("step", load_steps(), ids=lambda s: s["id"])
def test_every_snippet_runs_against_the_published_files(
    step: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.chdir(tmp_path)  # the download step writes files
    for lang, code in _variants(step):
        if lang == "sql":
            result = duckdb.connect().sql(code)
            shown = result.fetchall() if result is not None else "(no result)"
        elif code is None:
            # The site wraps the SQL for Python; run that same wrap.
            shown = duckdb.sql(fill(step["sql"]).rstrip().rstrip(";")).df()
        else:
            scope: dict = {}
            exec(code, scope)
            shown = {k: v for k, v in scope.items() if k in ("df", "wells", "samples", "well", "oil")}
        with capsys.disabled():
            print(f"\n[{step['id']} / {lang}]\n{shown}")
    if step["id"] == "download":
        assert len(list((tmp_path / "force_2020" / "wells").glob("*.parquet"))) == 108
        assert duckdb.sql("SELECT count(*) FROM 'force_2020_wells.parquet'").fetchone()[0] == 1307297
