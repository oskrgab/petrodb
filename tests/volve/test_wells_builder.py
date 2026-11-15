"""``build_wells`` flags ``has_production`` from both production sheets.

The committed ``wells.parquet`` is checked against the published production
tables in ``test_published_tables``; there every producing Wellbore is in both
sheets, so this test feeds ``build_wells`` small frames where one is not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

TRANSFORM = Path(__file__).resolve().parents[2] / "scripts" / "transform"


@pytest.fixture
def load_data(monkeypatch: pytest.MonkeyPatch):
    # load_data imports its siblings as top-level modules, as a script does.
    monkeypatch.syspath_prepend(str(TRANSFORM))
    import load_data

    yield load_data
    sys.modules.pop("load_data", None)


def _register() -> pd.DataFrame:
    def wellbore(name: str, npdid: str) -> dict:
        return {
            "wlbWellboreName": name,
            "wlbNpdidWellbore": npdid,
            "wlbField": "VOLVE",
            "fldNpdidField": "3420717",
            "wlbWellType": "DEVELOPMENT",
            "wlbPurpose": "PRODUCTION",
            "wlbContent": "OIL",
            "wlbCompletionYear": "2010",
            "wlbDiskosWellboreParent": None,
        }

    return pd.DataFrame(
        [wellbore("15/9-F-1", "1"), wellbore("15/9-F-2", "2"), wellbore("15/9-F-3", "3")]
    )


def _daily(npd_codes: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "NPD_WELL_BORE_CODE": npd_codes,
            "WELL_BORE_CODE": [f"NO {code}" for code in npd_codes],
            "NPD_WELL_BORE_NAME": [f"15/9-F-{code}" for code in npd_codes],
            "NPD_FIELD_CODE": [3420717] * len(npd_codes),
            "NPD_FIELD_NAME": ["VOLVE"] * len(npd_codes),
            "NPD_FACILITY_CODE": [369304] * len(npd_codes),
            "NPD_FACILITY_NAME": ["MÆRSK INSPIRER"] * len(npd_codes),
        }
    )


def _monthly(npd_codes: list[int]) -> pd.DataFrame:
    # As the sheet is read: its first row holds the units, not a Wellbore.
    return pd.DataFrame({"Wellbore name": [None, *map(str, npd_codes)],
                         "NPDCode": [None, *npd_codes]})  # fmt: skip


def test_a_wellbore_with_monthly_rows_only_has_production(load_data) -> None:
    wells = load_data.build_wells(_daily([1]), _monthly([1, 2]), _register())
    flags = dict(zip(wells["npd_wellbore_code"], wells["has_production"]))
    assert flags == {1: True, 2: True, 3: False}
