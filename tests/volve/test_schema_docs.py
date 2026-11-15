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
    assert set(schema["tables"]) == {
        "wells",
        "daily_production",
        "monthly_production",
        "petrophysical_interpretation",
    }
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


def test_wells_documents_every_column_with_its_nullability(exported: Path) -> None:
    # The production source's columns are empty for a Wellbore without
    # production; the register's content and completion year are empty for a
    # Wellbore that was never drilled, and the parent for an initial one.
    columns = json.loads((exported / "schema.json").read_text())["tables"]["wells"]["columns"]
    nullable = {c["name"]: not c["not_null"] for c in columns}
    assert nullable == {
        "npd_wellbore_code": False,
        "wellbore_code": True,
        "wellbore_name": False,
        "npd_field_code": False,
        "npd_field_name": False,
        "npd_facility_code": True,
        "npd_facility_name": True,
        "wellbore_type": False,
        "purpose": False,
        "content": True,
        "completion_year": True,
        "parent_npd_wellbore_code": True,
        "has_production": False,
    }
    md_rows = {
        row[1]: row[2].split("|")[1].strip()
        for row in re.finditer(r"^\| `([^`]+)` \|(.*)\|\s*$", _wells_section(exported), re.M)
    }
    assert {name: flag == "Yes" for name, flag in md_rows.items()} == nullable
    sql = (exported / "schema.sql").read_text()
    wells_ddl = sql[sql.index("CREATE TABLE wells") :].split(";", 1)[0]
    for name, is_nullable in nullable.items():
        line = next(
            line for line in wells_ddl.splitlines() if line.strip().startswith(f"{name} ")
        )
        assert ("NOT NULL" not in line) == is_nullable, line


def test_petrophysical_interpretation_documents_its_key_and_every_curve(exported: Path) -> None:
    table = json.loads((exported / "schema.json").read_text())["tables"][
        "petrophysical_interpretation"
    ]
    columns = [(c["name"], c["type"], c["not_null"], c["primary_key"]) for c in table["columns"]]
    assert columns[:3] == [
        ("npd_wellbore_code", "INTEGER", True, False),
        ("source_wellbore", "TEXT", True, True),
        ("depth_md", "DOUBLE", True, True),
    ]
    curves = columns[3:]
    # Every Curve the eight LAS pairs carry, named with the source mnemonic.
    assert [name for name, *_ in curves] == [
        "ABDCQF01", "ABDCQF02", "ABDCQF03", "ABDCQF04", "BS", "CALI", "DRHO",
        "DT", "DTS", "GR", "NBGRCFM", "NPHI", "PEF", "RACEHM", "RACELM", "RD",
        "RHOB", "RM", "ROP", "ROP5_RM", "RPCEHM", "RPCELM", "RS", "RT",
        "BADDATA_FLAG", "BVW", "CARB_FLAG", "COAL_FLAG", "KLOGH", "PHIF",
        "SAND_FLAG", "SW", "VCARB", "VSH",
    ]  # fmt: skip
    assert {(type_, not_null, pk) for _, type_, not_null, pk in curves} == {
        ("DOUBLE", False, False)
    }
    assert table["foreign_keys"] == [
        {
            "column": "npd_wellbore_code",
            "references_table": "wells",
            "references_column": "npd_wellbore_code",
        }
    ]


def _wells_section(exported: Path) -> str:
    markdown = (exported / "schema.md").read_text()
    return markdown[markdown.index("### `wells`") :].split("\n---\n", 1)[0]


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
