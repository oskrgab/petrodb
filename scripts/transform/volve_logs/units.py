"""The committed unit table: one documented unit per Curve, and the source spellings of it.

The source files spell one unit several ways (``v/v``, ``V/V``,
``v/v_decimal``) and leave some unknown (``UNKNOWN``). This table records what
each spelling means; values are never converted, so a spelling may only map
to the unit already documented for its column.

- ``CURVE_UNITS``: the one unit documented for each Curve column, written as
  the schema documents write it.
- ``SPELLINGS``: what a source spelling means, whatever the mnemonic.
- ``MNEMONIC_SPELLINGS``: what a spelling means for one mnemonic only. It is
  read first. It holds the spellings that do not name a unit on their own
  (``UNKNOWN``, or a blank), or that name another unit than the column's (``V/V`` on a
  flag, ``MD`` on a permeability), where the values show which unit the file
  means.

``check`` fails the build on a spelling neither table knows
(``UnitSpellingError``) and on one that maps to a unit other than the
column's (``UnitMismatchError``), naming the file, the mnemonic and the
spelling. A new spelling is added here, by review, never mapped silently.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa

UNIT_METADATA_KEY = b"unit"

G_CM3 = "g/cm³"
INCH = "in"
US_FT = "µs/ft"
GAPI = "gAPI"
FRACTION = "v/v"
B_E = "b/e"
OHM_M = "ohm·m"
M_H = "m/h"
MILLIDARCY = "mD"
UNITLESS = "unitless"
DEG_C = "°C"

CURVE_UNITS: dict[str, str] = {
    "ABDCQF01": G_CM3,
    "ABDCQF02": G_CM3,
    "ABDCQF03": G_CM3,
    "ABDCQF04": G_CM3,
    "BS": INCH,
    "CALI": INCH,
    "DRHB": G_CM3,
    "DRHO": G_CM3,
    "DRHU": G_CM3,
    "DT": US_FT,
    "DTS": US_FT,
    "GR": GAPI,
    "NBGRCFM": GAPI,
    "NPHI": FRACTION,
    "PEF": B_E,
    "RACEHM": OHM_M,
    "RACELM": OHM_M,
    "RD": OHM_M,
    "RHOB": G_CM3,
    "RM": OHM_M,
    "ROBB": G_CM3,
    "ROBU": G_CM3,
    "ROP": M_H,
    "ROP5_RM": M_H,
    "RPCEHM": OHM_M,
    "RPCELM": OHM_M,
    "RS": OHM_M,
    "RT": OHM_M,
    "BADDATA_FLAG": UNITLESS,
    "BVW": FRACTION,
    "CARB_FLAG": UNITLESS,
    "COAL_FLAG": UNITLESS,
    "KLOGH": MILLIDARCY,
    "PHID": FRACTION,
    "PHIF": FRACTION,
    "SAND_FLAG": UNITLESS,
    "SW": FRACTION,
    "VCARB": FRACTION,
    "VSH": FRACTION,
    # Only the 15/9-19 interpretation files carry these.
    "BWV": FRACTION,
    "DELTA": FRACTION,
    "GRMAX": GAPI,
    "GRMIN": GAPI,
    "J": UNITLESS,
    "KLHC_INT": MILLIDARCY,
    "KLOGV": MILLIDARCY,
    "M": UNITLESS,
    "N": UNITLESS,
    "PERF_FLAG": UNITLESS,
    "PORD": FRACTION,
    "RHOFL": G_CM3,
    "RHOMA": G_CM3,
    "RW": OHM_M,
    "SWIRR": FRACTION,
    "TEMP": DEG_C,
}

SPELLINGS: dict[str, str] = {
    "g/cm3": G_CM3,
    "G/CC": G_CM3,
    "G/C3": G_CM3,
    "G/CM3": G_CM3,
    "inches": INCH,
    "IN": INCH,
    "us/ft": US_FT,
    "US/F": US_FT,
    "US/FT": US_FT,
    "API": GAPI,
    "GAPI": GAPI,
    "v/v": FRACTION,
    "V/V": FRACTION,
    "v/v_decimal": FRACTION,
    "b/elec": B_E,
    "B/E": B_E,
    "ohm.m": OHM_M,
    "OHMM": OHM_M,
    "m/hr": M_H,
    "mD": MILLIDARCY,
    "unitless": UNITLESS,
    "UNITLESS": UNITLESS,
    "DEGC": DEG_C,
}

MNEMONIC_SPELLINGS: dict[tuple[str, str], str] = {
    # 15/9-F-1 B writes its carbonate flag as a fraction; its values are 0 and 1.
    ("CARB_FLAG", "V/V"): UNITLESS,
    # 15/9-F-1, several DLIS files and the 15/9-19 files write the
    # permeability unit in capitals.
    ("KLOGH", "MD"): MILLIDARCY,
    ("KLOGV", "MD"): MILLIDARCY,
    ("KLHC_INT", "MD"): MILLIDARCY,
    # Files that leave the unit unknown. The values show the unit: the
    # resistivities lie in the range the same Curves have in ohm·m in the
    # other files, the second rate of penetration (15/9-F-12 only) in the
    # range ROP has in m/h in the other Wellbores, and the flags are 0 and 1.
    ("RACEHM", "UNKNOWN"): OHM_M,
    ("RACELM", "UNKNOWN"): OHM_M,
    ("RPCEHM", "UNKNOWN"): OHM_M,
    ("RPCELM", "UNKNOWN"): OHM_M,
    ("RD", "UNKNOWN"): OHM_M,
    ("RS", "UNKNOWN"): OHM_M,
    ("ROP5_RM", "UNKNOWN"): M_H,
    ("CARB_FLAG", "UNKNOWN"): UNITLESS,
    ("COAL_FLAG", "UNKNOWN"): UNITLESS,
    ("SAND_FLAG", "UNKNOWN"): UNITLESS,
    # The 15/9-19 files leave some units blank. The Leverett J-function and
    # the saturation exponent are dimensionless; the irreducible water
    # saturation is a fraction, and so is BWV in 15/9-19 SR (its values lie
    # between 0 and 0.35, the range of the file's porosity). 15/9-19 SR's
    # sonic lies in the range DT has in µs/ft in the other Wellbores (median
    # about 75).
    ("J", ""): UNITLESS,
    ("N", ""): UNITLESS,
    ("SWIRR", ""): FRACTION,
    ("BWV", ""): FRACTION,
    ("DT", ""): US_FT,
}


class UnitSpellingError(Exception):
    """A source file spells a unit the unit table does not know."""


class UnitMismatchError(Exception):
    """A source spelling means a unit other than the one documented for its column."""


def check(path: Path, table: pa.Table) -> None:
    """Fail unless every Curve of ``table``, read from ``path``, is in its column's unit.

    Each Curve field carries its source spelling as ``unit`` field metadata
    (an empty spelling is one the table does not know). A mnemonic with no
    documented unit is not checked here: the build fails on it as
    undocumented.
    """
    for field in table.schema:
        if field.name not in CURVE_UNITS:
            continue
        spelling = (field.metadata or {}).get(UNIT_METADATA_KEY, b"").decode()
        documented = CURVE_UNITS[field.name]
        unit = MNEMONIC_SPELLINGS.get((field.name, spelling), SPELLINGS.get(spelling))
        if unit is None:
            raise UnitSpellingError(
                f"{path}: Curve {field.name} has unit spelling {spelling!r}, "
                f"which the unit table does not know (documented unit {documented!r})"
            )
        if unit != documented:
            raise UnitMismatchError(
                f"{path}: Curve {field.name} has unit spelling {spelling!r}, which "
                f"means {unit!r}, not the documented unit {documented!r}"
            )
