"""Unit tests for the Argentina `website_integrator`.

Verifies:

- The root `README.md` gains an Argentina entry under `## Datasets`.
- The patch is idempotent: re-running produces a byte-identical file and
  never duplicates the entry.
- The patch is bracketed by sentinel HTML comments so it can be
  removed/replaced.
- It writes no markup anywhere else: the Landing reads the Dataset
  metadata under `site/data/` (ADR-0010).
"""

from pathlib import Path

import pytest

from scripts.export.argentina import website_integrator

# A tiny but representative root README. The anchor must match the
# production README.md structure exactly.
_README_BEFORE = """\
# PetroData Repository

Open petroleum datasets in Parquet format for data science and machine learning applications.

## Datasets

### Volve Production Data
Production metrics from the Equinor Volve oil field (2007-2016):
- 7 wells, 15K daily measurements, 526 monthly aggregates.

### FORCE 2020 Well Logs
Well log data from 108 wells in the Norwegian Continental Shelf.

## Access Data

Browse and download files at: **https://dev-petrodb.ocortez.com**

## License

See original license terms.
"""


@pytest.fixture
def website_root(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text(_README_BEFORE)
    return tmp_path


def test_integrate_adds_argentina_blurb_to_root_readme(website_root: Path) -> None:
    website_integrator.integrate(website_root)
    body = (website_root / "README.md").read_text()
    assert "### Argentina Production Data" in body
    assert "wells.parquet" in body
    assert "well_operator_history.parquet" in body
    assert "well_events.parquet" in body
    assert "monthly_production" in body
    # Spanish column names are mentioned (the contract from CONTEXT.md)
    assert "Spanish" in body or "español" in body.lower()


def test_integrate_readme_blurb_appears_under_datasets(website_root: Path) -> None:
    """The Argentina entry must sit under `## Datasets` and before
    `## Access Data` so it slots in next to Volve and FORCE 2020."""
    website_integrator.integrate(website_root)
    body = (website_root / "README.md").read_text()
    datasets_idx = body.index("## Datasets")
    argentina_idx = body.index("### Argentina Production Data")
    access_idx = body.index("## Access Data")
    assert datasets_idx < argentina_idx < access_idx


def test_integrate_readme_includes_duckdb_query_example(website_root: Path) -> None:
    """The blurb must carry a copy-pasteable DuckDB query example."""
    website_integrator.integrate(website_root)
    body = (website_root / "README.md").read_text()
    assert "import json, urllib.request, duckdb" in body
    assert "duckdb.sql(" in body
    # The example uses the published HTTP URLs so it works without download
    # (dev Caddy host is the no-env fallback; CI sets BASE_URL to the HF base).
    assert "https://dev-petrodb.ocortez.com/argentina/" in body
    # And exercises the partitioned monthly series via manifest-based discovery,
    # never a glob (ADR-0004): the file list comes from `_files.json`.
    assert "monthly_production/anio=*/data.parquet" not in body
    assert "_files.json" in body
    assert "read_parquet(?" in body
    assert "hive_partitioning = true" in body


def test_integrate_is_idempotent_on_root_readme(website_root: Path) -> None:
    website_integrator.integrate(website_root)
    first = (website_root / "README.md").read_text()
    website_integrator.integrate(website_root)
    second = (website_root / "README.md").read_text()
    assert first == second


def test_integrate_does_not_duplicate_argentina_entries(website_root: Path) -> None:
    """Re-running must never accumulate copies of the inserted entries."""
    for _ in range(3):
        website_integrator.integrate(website_root)
    readme = (website_root / "README.md").read_text()
    assert readme.count("### Argentina Production Data") == 1


def test_integrate_writes_sentinel_markers(website_root: Path) -> None:
    """The sentinels are how the patch finds itself on a re-run; if they
    disappear, the patch will duplicate."""
    website_integrator.integrate(website_root)
    readme = (website_root / "README.md").read_text()
    assert website_integrator.README_BEGIN in readme
    assert website_integrator.README_END in readme


def test_integrate_replaces_stale_block_in_place(website_root: Path) -> None:
    """If the inserted block changes, re-running must overwrite the prior
    version rather than appending alongside it."""
    website_integrator.integrate(website_root)
    readme_path = website_root / "README.md"
    body = readme_path.read_text()
    # Doctor the file so the previous block contains stale text.
    stale = body.replace(
        "### Argentina Production Data",
        "### Argentina Production Data\nSTALE STALE STALE",
        1,
    )
    readme_path.write_text(stale)
    assert "STALE STALE STALE" in readme_path.read_text()

    website_integrator.integrate(website_root)
    fresh = readme_path.read_text()
    assert "STALE STALE STALE" not in fresh
    assert fresh.count("### Argentina Production Data") == 1


def test_integrate_writes_only_the_root_readme(website_root: Path) -> None:
    """Pipelines emit data, never markup (ADR-0010): the README is the one
    file the integrator touches."""
    website_integrator.integrate(website_root)
    assert sorted(p.name for p in website_root.rglob("*")) == ["README.md"]
