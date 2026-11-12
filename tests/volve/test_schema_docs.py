"""Volve's schema documents describe every column, and say the same thing twice.

The Landing's Tables section reads column descriptions from ``schema.md``;
tooling reads ``schema.json``. Both are generated from one export schema
definition, so they cannot disagree.
"""

import json
import re
from pathlib import Path

import pytest

from scripts.export import export_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = REPO_ROOT / "parquet" / "volve"


def _md_descriptions(markdown: str) -> dict[str, dict[str, str]]:
    """table -> column -> description, read the way the Landing reads it."""
    out: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in markdown.splitlines():
        heading = re.match(r"^### `([^`]+)`", line)
        if heading:
            current = out.setdefault(heading[1], {})
            continue
        row = re.match(r"^\| `([^`]+)` \|(.*)\|\s*$", line)
        if row and current is not None:
            current[row[1]] = row[2].split("|")[-1].strip()
    return out


@pytest.fixture(scope="module")
def exported(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("volve")
    export_schema.export_all_schemas(output_dir=out)
    return out


def test_every_column_has_a_description_in_schema_json(exported: Path) -> None:
    schema = json.loads((exported / "schema.json").read_text())
    assert set(schema["tables"]) == {"wells", "daily_production", "monthly_production"}
    for table, meta in schema["tables"].items():
        assert meta["description"], table
        for column in meta["columns"]:
            assert column["description"], f"{table}.{column['name']}"


def test_schema_md_carries_the_same_descriptions(exported: Path) -> None:
    schema = json.loads((exported / "schema.json").read_text())
    described = _md_descriptions((exported / "schema.md").read_text())
    for table, meta in schema["tables"].items():
        expected = {c["name"]: c["description"] for c in meta["columns"]}
        assert described[table] == expected, table


def test_published_documents_are_current(exported: Path) -> None:
    for name in ("schema.json", "schema.md", "schema.sql"):
        assert (PUBLISHED / name).read_text() == (exported / name).read_text(), (
            f"re-run `uv run -m scripts.export.export_schema` ({name})"
        )


def test_a_description_for_a_column_that_does_not_exist_is_an_error() -> None:
    with pytest.raises(ValueError, match="no_such_column"):
        export_schema.check_descriptions(
            {"wells": ["npd_wellbore_code"]},
            {"wells": {"npd_wellbore_code": "x", "no_such_column": "y"}},
        )
