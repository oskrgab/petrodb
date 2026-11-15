"""Every surface that states the Volve licence states the current one.

Equinor replaced the CC BY-NC-SA 4.0 terms with its own open data licence,
based on CC BY 4.0: the data may be shared and adapted, for commercial use
too, but may not be sold, and every copy must credit Equinor and the former
Volve licence partners and link to the licence text. The pinned facts below
come from that text (the Volve terms and conditions PDF on Equinor's CDN).
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

LICENCE_NAME = "Equinor Open Data Licence"
LICENCE_URL = (
    "https://cdn.equinor.com/files/h61q9gi9/global/"
    "de6532f6134b9a953f6c41bac47a0c055a3712d3.pdf"
)
FORMER_PARTNERS = (
    "ExxonMobil Exploration & Production Norway AS",
    "Bayerngas Norge AS",
)

VOLVE_META = json.loads((REPO_ROOT / "site" / "data" / "volve" / "dataset.json").read_text())

SURFACES = [
    "LICENSE-VOLVE-DATA.md",
    "README.md",
    "hf/README.md",
    "site/data/volve/dataset.json",
]


@pytest.mark.parametrize("surface", SURFACES)
def test_no_surface_still_states_the_old_non_commercial_licence(surface: str) -> None:
    text = (REPO_ROOT / surface).read_text()
    assert "NC-SA" not in text.upper()
    assert "by-nc-sa" not in text.lower()


@pytest.mark.parametrize("surface", SURFACES)
def test_every_surface_names_the_licence_and_links_its_text(surface: str) -> None:
    text = (REPO_ROOT / surface).read_text()
    assert LICENCE_NAME in text
    assert LICENCE_URL in text


def test_landing_metadata_names_the_licence_and_links_its_text() -> None:
    assert VOLVE_META["licence"]["name"] == LICENCE_NAME
    assert VOLVE_META["licence"]["url"] == LICENCE_URL


def test_landing_note_says_share_and_adapt_with_credit_but_never_sell() -> None:
    note = VOLVE_META["licence"]["note"]
    assert "may not be sold" in note
    assert "share" in note and "adapt" in note
    assert "former Volve licence partners" in note


@pytest.mark.parametrize("partner", FORMER_PARTNERS)
def test_licence_file_credits_each_former_licence_partner(partner: str) -> None:
    text = (REPO_ROOT / "LICENSE-VOLVE-DATA.md").read_text()
    assert partner in text


def test_licence_file_gives_the_terms_in_the_licence_own_words() -> None:
    text = (REPO_ROOT / "LICENSE-VOLVE-DATA.md").read_text()
    assert "You may not sell the Licensed Material." in text
    assert "Share the Licensed Material and/or the Adapted Material" in text
    assert "Create, produce and reproduce Adapted Material" in text
