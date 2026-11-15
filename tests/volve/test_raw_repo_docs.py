"""The Raw repo's own README and licence notes, committed here ready to upload."""

import subprocess
from pathlib import Path

from scripts.raw_repo.volve import upload_plan

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "hf" / "petrodb-raw-volve"
OFFICIAL_LICENCE = (
    "https://www.equinor.com/content/dam/statoil/documents/what-we-do/"
    "Equinor-HRS-Terms-and-conditions-for-licence-to-data-Volve.pdf"
)
PARTNERS = "ExxonMobil Exploration &\nProduction Norway AS and Bayerngas Norge AS"


def _front_matter(markdown: str) -> list[str]:
    _, front, _ = markdown.split("---\n", 2)
    return front.splitlines()


def test_dataset_card_declares_a_custom_licence_with_its_licence_file() -> None:
    front = _front_matter((DOCS / "README.md").read_text())

    assert "license: other" in front
    assert "license_link: LICENSE.md" in front
    assert any(line.startswith("license_name: ") for line in front)


def test_readme_states_every_adjustment_to_upstream() -> None:
    readme = (DOCS / "README.md").read_text()

    for target in upload_plan.BY_TYPE_ADDITIONS.values():
        assert f"`{target}`" in readme
    assert "junk" in readme
    assert "by-type tree is left out" in readme


def test_readme_cites_the_operators_official_source() -> None:
    assert (
        "https://www.equinor.com/energy/volve-data-sharing"
        in (DOCS / "README.md").read_text()
    )


def test_licence_note_links_the_official_text_and_attributes_the_former_partners() -> (
    None
):
    licence = (DOCS / "LICENSE.md").read_text()

    assert OFFICIAL_LICENCE in licence
    assert "© Equinor and the former Volve licence partners" in licence
    assert PARTNERS in licence
    assert "may not sell" in licence


def test_register_folder_carries_its_own_nlod_note() -> None:
    note = (DOCS / "register" / "LICENSE.md").read_text()

    assert "Norwegian licence for Open Government data (NLOD)" in note
    assert "Norwegian Offshore Directorate" in note


def test_local_raw_directory_is_gitignored_but_its_readme_and_pin_are_not() -> None:
    def ignored(relpath: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", relpath],
            cwd=REPO_ROOT,
            check=False,
        )
        return result.returncode == 0

    assert ignored("data/raw/volve/Well_logs_pr_WELL/15_9-F-1/x.las")
    assert ignored("data/raw/volve/README.md")
    assert not ignored("data/raw/README.md")
    assert not ignored("data/raw/volve.pin")
