"""The Dataset metadata for Argentina and Petrobras 3W carries what their pages show.

These two Datasets used to reach the Landing as HTML that their export
pipelines spliced into ``parquet/index.html``, with tests asserting on that
markup. The Landing now builds each page from ``site/data/<dataset>/``
(ADR-0010), so the same facts are pinned there: the published tables, the
source attribution and the licence.
"""

import json
from pathlib import Path

import pytest

from scripts.transform.petrobras_3w.constants import UPSTREAM_REPO_URL

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DATA = REPO_ROOT / "site" / "data"
PARQUET = REPO_ROOT / "parquet"

CC_BY_4 = "https://creativecommons.org/licenses/by/4.0/"


def _read(dataset: str, name: str):
    return json.loads((SITE_DATA / dataset / name).read_text())


def test_argentina_lists_its_four_published_tables() -> None:
    tables = {t["name"]: t for t in _read("argentina", "files.json")}
    assert set(tables) == {
        "wells",
        "well_operator_history",
        "well_events",
        "monthly_production",
    }
    assert tables["monthly_production"]["manifest"] == "monthly_production/_files.json"


def test_argentina_lists_every_year_of_monthly_production() -> None:
    monthly = next(
        t for t in _read("argentina", "files.json") if t["name"] == "monthly_production"
    )
    years = [f["path"].split("anio=")[1].split("/")[0] for f in monthly["files"]]
    assert years == [str(y) for y in range(2006, 2026)]
    manifest = json.loads(
        (PARQUET / "argentina" / "monthly_production" / "_files.json").read_text()
    )
    assert [f["path"] for f in monthly["files"]] == [
        f"monthly_production/{p}" for p in manifest
    ]


@pytest.mark.parametrize("doc", ["README.md", "schema.md", "schema.json", "schema.sql"])
def test_argentina_schema_documents_exist_for_the_page_to_serve(doc: str) -> None:
    assert (PARQUET / "argentina" / doc).is_file()


def test_argentina_credits_the_secretaria_de_energia_under_cc_by() -> None:
    meta = _read("argentina", "dataset.json")
    assert (
        "datos.energia.gob.ar/dataset/produccion-de-petroleo-y-gas-por-pozo"
        in meta["source"]["text"]
    )
    assert "Secretaría de Energía" in meta["source"]["text"]
    assert meta["licence"]["url"] == CC_BY_4


def test_petrobras_3w_credits_the_upstream_repository_under_cc_by() -> None:
    meta = _read("petrobras_3w", "dataset.json")
    assert UPSTREAM_REPO_URL.removesuffix(".git") in meta["source"]["text"]
    assert meta["licence"]["url"] == CC_BY_4


def test_petrobras_3w_page_is_built_from_its_generated_tree() -> None:
    # Its tree is gitignored and built in CI, so no file list is committed:
    # the site build lists it from disk (ADR-0010).
    assert _read("petrobras_3w", "dataset.json")["generated"] is True
    assert not (SITE_DATA / "petrobras_3w" / "files.json").exists()
