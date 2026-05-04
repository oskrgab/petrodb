"""Unit tests for the Argentina export validator.

Currently exercises the WKB-parseability invariant. Later issues add
PK uniqueness, FK integrity, date completeness, partition counts.
"""

import duckdb
import pytest

from scripts.export.argentina import validator

VALID_WKB_HEX = "0101000020E61000000000000000405140000000000000C040"
INVALID_WKB_HEX = "DEADBEEFCAFEBABEDEADBEEFCAFEBABE"


def _make_wells_with_geom(
    con: duckdb.DuckDBPyConnection, hex_values: list[str | None]
) -> None:
    con.execute("CREATE OR REPLACE TABLE wells (idpozo INTEGER, geom BLOB)")
    for i, hx in enumerate(hex_values, start=1):
        if hx is None:
            con.execute("INSERT INTO wells VALUES (?, NULL)", [i])
        else:
            con.execute(
                "INSERT INTO wells VALUES (?, unhex(?))",
                [i, hx],
            )


def test_validator_passes_on_valid_wkb():
    con = duckdb.connect()
    _make_wells_with_geom(con, [VALID_WKB_HEX, VALID_WKB_HEX])
    validator.validate(con)


def test_validator_passes_when_geom_is_null():
    """NULL geom rows are skipped (the invariant only applies to non-NULL rows)."""
    con = duckdb.connect()
    _make_wells_with_geom(con, [VALID_WKB_HEX, None, None])
    validator.validate(con)


def test_validator_raises_on_invalid_wkb():
    con = duckdb.connect()
    _make_wells_with_geom(con, [VALID_WKB_HEX, INVALID_WKB_HEX])
    with pytest.raises(Exception):
        validator.validate(con)
