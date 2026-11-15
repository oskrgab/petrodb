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
        "log_curves",
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
    # Every Curve the LAS and DLIS sources carry, named with the source
    # mnemonic, in the order the pipeline writes them from the real raw files:
    # by how many of the 17 Wellbores carry the Curve (9 in all 17, then 16,
    # 15, 13, 12, 9, 8, 7, 6, 5, 3, 2 and 1), ties by mnemonic.
    assert [name for name, *_ in curves] == [
        "BVW", "COAL_FLAG", "GR", "KLOGH", "NPHI", "RHOB", "RT", "SAND_FLAG", "VSH",
        "PHIF", "RD", "SW",
        "DRHO",
        "CALI", "CARB_FLAG", "DT",
        "PEF",
        "RS",
        "ABDCQF01", "ABDCQF02", "ABDCQF03", "ABDCQF04", "BS", "RACEHM", "RACELM",
        "ROP", "RPCEHM", "RPCELM",
        "RM",
        "DTS",
        "VCARB",
        "DRHU", "NBGRCFM", "ROBU",
        "ROBB",
        "BADDATA_FLAG", "DRHB", "PHID", "ROP5_RM",
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


def test_petrophysical_interpretation_states_its_layout(exported: Path) -> None:
    description = json.loads((exported / "schema.json").read_text())["tables"][
        "petrophysical_interpretation"
    ]["description"]
    assert "single row group" in description
    assert "descending order of how many wellbores carry them, ties by mnemonic" in description
    assert description in (exported / "schema.md").read_text()


def test_every_curve_has_one_unit_in_schema_json_and_schema_md(exported: Path) -> None:
    columns = json.loads((exported / "schema.json").read_text())["tables"][
        "petrophysical_interpretation"
    ]["columns"]
    units = {c["name"]: c["unit"] for c in columns}
    assert units == {
        "npd_wellbore_code": None,
        "source_wellbore": None,
        "depth_md": "m",
        **{name: "g/cm³" for name in ("ABDCQF01", "ABDCQF02", "ABDCQF03", "ABDCQF04")},
        "BS": "in",
        "CALI": "in",
        **{name: "g/cm³" for name in ("DRHB", "DRHO", "DRHU", "ROBB", "ROBU")},
        "DT": "µs/ft",
        "DTS": "µs/ft",
        "GR": "gAPI",
        "NBGRCFM": "gAPI",
        "NPHI": "v/v",
        "PEF": "b/e",
        **{name: "ohm·m" for name in ("RACEHM", "RACELM", "RD", "RM", "RPCEHM", "RPCELM", "RS", "RT")},
        "RHOB": "g/cm³",
        "ROP": "m/h",
        "ROP5_RM": "m/h",
        **{name: "unitless" for name in ("BADDATA_FLAG", "CARB_FLAG", "COAL_FLAG", "SAND_FLAG")},
        **{name: "v/v" for name in ("BVW", "PHID", "PHIF", "SW", "VCARB", "VSH")},
        "KLOGH": "mD",
    }  # fmt: skip
    markdown = (exported / "schema.md").read_text()
    section = markdown[markdown.index("### `petrophysical_interpretation`") :].split("\n---\n", 1)[0]
    assert "| Column | Type | Unit | Nullable | Primary Key | Description |" in section
    md_units = {
        row[1]: row[2].split("|")[1].strip()
        for row in re.finditer(r"^\| `([^`]+)` \|(.*)\|\s*$", section, re.M)
    }
    assert md_units == {name: unit or "—" for name, unit in units.items()}


def test_log_curves_documents_its_key_every_column_and_the_depth_unit(exported: Path) -> None:
    table = json.loads((exported / "schema.json").read_text())["tables"]["log_curves"]
    columns = [
        (c["name"], c["type"], c["unit"], c["not_null"], c["primary_key"])
        for c in table["columns"]
    ]
    assert columns == [
        ("table_name", "TEXT", None, True, True),
        ("npd_wellbore_code", "INTEGER", None, True, False),
        ("source_wellbore", "TEXT", None, True, True),
        ("mnemonic", "TEXT", None, True, True),
        ("curve_kind", "TEXT", None, True, False),
        ("unit", "TEXT", None, True, False),
        ("source_unit", "TEXT", None, True, False),
        ("first_depth_md", "DOUBLE", "m", True, False),
        ("last_depth_md", "DOUBLE", "m", True, False),
        ("sample_count", "INTEGER", None, True, False),
        ("source_file", "TEXT", None, True, False),
    ]
    assert table["foreign_keys"] == [
        {
            "column": "npd_wellbore_code",
            "references_table": "wells",
            "references_column": "npd_wellbore_code",
        }
    ]
    described = _md_descriptions((exported / "schema.md").read_text())["log_curves"]
    assert "`input`" in described["curve_kind"] and "`interpreted`" in described["curve_kind"]
    assert "Raw repo" in described["source_file"]


def test_a_documented_curve_without_a_unit_is_an_error() -> None:
    with pytest.raises(ValueError, match="RHOB: no documented unit"):
        export_schema.check_curve_units(("GR", "RHOB"), {"GR": "gAPI"})


def test_tables_without_units_keep_their_document_layout(exported: Path) -> None:
    schema = json.loads((exported / "schema.json").read_text())["tables"]
    for table in ("wells", "daily_production", "monthly_production"):
        assert all("unit" not in c for c in schema[table]["columns"]), table
    assert "| Column | Type | Nullable | Primary Key | Description |" in _wells_section(exported)


def test_source_wellbore_explains_technical_sidetracks_and_their_parent(exported: Path) -> None:
    described = _md_descriptions((exported / "schema.md").read_text())
    source = described["petrophysical_interpretation"]["source_wellbore"]
    assert "Technical sidetrack" in source
    assert "`15/9-F-11 T2`" in source
    assert "parent" in source
    assert "top-hole" in source


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
