"""Synthetic LAS files laid out like the Volve Raw repo, written at test time.

Every file is generated with ``lasio`` into a temporary directory; no real log
file and no network is needed. The tree holds, under the upstream folder
names, one LAS pair for each of the eight Wellbores the petrophysical
interpretation reads as LAS pairs, the LAS pair of the Technical sidetrack
15/9-F-11 T2, the input file of the 15/9-F-11 top-hole section, and the
single interpretation file of each 15/9-19 wellbore, which holds Input curves
and Interpreted curves together. Beside them sits a geomodel permeability
export the build must not read.
"""

from __future__ import annotations

import json
from pathlib import Path

import lasio

SENTINEL = -999.25
SCHEMA = Path(__file__).resolve().parents[2] / "parquet" / "volve" / "schema.json"
INTERPRETATION = "05.PETROPHYSICAL INTERPRETATION"

# Upstream folder -> (operator's name, npd_wellbore_code), as the register has them.
WELLBORES = {
    "15_9-F-1": ("15/9-F-1", 7223),
    "15_9-F-1 A": ("15/9-F-1 A", 7224),
    "15_9-F-1 B": ("15/9-F-1 B", 7264),
    "15_9-F-1 C": ("15/9-F-1 C", 7405),
    "15_9-F-11 A": ("15/9-F-11 A", 7079),
    "15_9-F-11 B": ("15/9-F-11 B", 7080),
    "15_9-F-12": ("15/9-F-12", 5599),
    "15_9-F-15 D": ("15/9-F-15 D", 7289),
}

# The Technical sidetrack: not in the register, so its rows take the parent
# Wellbore's npd_wellbore_code, 15/9-F-11.
TECHNICAL_SIDETRACK = ("15_9-F-11 T2", "15/9-F-11 T2", 7078)
# The 15/9-F-11 top-hole section: an input file and no output file.
TOP_HOLE = ("15_9-F-11", "15/9-F-11", 7078)

# The 15/9-19 wellbores: one LAS interpretation file each, in a CPI folder.
# Upstream folder -> (file, operator's name, npd_wellbore_code). 15/9-19 BT2
# is a Technical sidetrack: its rows take the code of 15/9-19 B.
SINGLE_FILES = {
    "15_9-19 A": ("15_9-19_A_CPI.las", "15/9-19 A", 3145),
    "15_9-19 B&BT2": ("15_9-19_BT2_CPI.las", "15/9-19 BT2", 3251),
    "15_9-19 S&SR": ("15_9-19_SR_CPI.las", "15/9-19 SR", 2105),
}

Curves = dict[str, tuple[str, list[float]]]  # mnemonic -> (unit, values)


def write_las(path: Path, depths: list[float], curves: Curves, well: str = "") -> Path:
    """A LAS 2.0 file with a DEPTH index in metres and the given Curves."""
    las = lasio.LASFile()
    las.well["NULL"].value = SENTINEL
    # A header that names some other well: the build must use the folder.
    las.well["WELL"].value = well
    las.append_curve("DEPTH", depths, unit="M", descr="Depth")
    for mnemonic, (unit, values) in curves.items():
        las.append_curve(mnemonic, values, unit=unit)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        las.write(f, version=2.0, fmt="%.8f")
    return path


def pair_paths(raw: Path, folder: str) -> tuple[Path, Path]:
    base = raw / "Well_logs_pr_WELL" / folder / INTERPRETATION
    return (
        base / "WLC_PETRO_COMPUTED_INPUT_1.LAS",
        base / "WLC_PETRO_COMPUTED_OUTPUT_1.LAS",
    )


def single_file_path(raw: Path, folder: str) -> Path:
    return raw / "Well_logs_pr_WELL" / folder / INTERPRETATION / "CPI" / SINGLE_FILES[folder][0]


def build_raw_tree(raw: Path) -> Path:
    """The fixture raw directory. 15/9-F-1 carries the interesting cases.

    15/9-F-1, input at 1000.0 .. 1000.4 m, output at 1000.2 .. 1000.5 m:

    - 1000.0: every Input curve is a sentinel, and the output has no sample:
      an all-NULL row, dropped;
    - 1000.1: GR is a sentinel, RHOB is not;
    - 1000.2 .. 1000.4: both files, VSH in both and equal;
    - 1000.5: only the output has a sample.

    15/9-F-12 has depths in feet steps written with float noise, and a
    geomodel permeability export whose KLOGH must not be read.

    15/9-19 A's single file holds the Input curve BS beside the Interpreted
    curves PHIF and TEMP, in spellings only these files use (``IN``,
    ``DEGC``), and an all-sentinel last row. 15/9-19 SR's DT has a blank
    unit spelling.
    """
    write_las(
        pair_paths(raw, "15_9-F-1")[0],
        [1000.0, 1000.1, 1000.2, 1000.3, 1000.4],
        {
            "GR": ("API", [SENTINEL, SENTINEL, 50.0, 60.0, 70.0]),
            "RHOB": ("g/cm3", [SENTINEL, 2.31, 2.32, 2.33, 2.34]),
            "VSH": ("v/v", [SENTINEL, SENTINEL, 0.5, 0.6, SENTINEL]),
        },
        well="SOME OTHER NAME",
    )
    write_las(
        pair_paths(raw, "15_9-F-1")[1],
        [1000.2, 1000.3, 1000.4, 1000.5],
        {
            "PHIF": ("V/V", [0.21, 0.22, 0.23, 0.24]),
            "COAL_FLAG": ("unitless", [0.0, 1.0, 0.0, 0.0]),
            "VSH": ("V/V", [0.5, 0.6, SENTINEL, SENTINEL]),
        },
    )
    for folder in WELLBORES:
        if folder in ("15_9-F-1", "15_9-F-12"):
            continue
        write_las(pair_paths(raw, folder)[0], [2000.0, 2000.1], {"GR": ("API", [80.0, 81.0])})
        write_las(pair_paths(raw, folder)[1], [2000.1], {"SW": ("v/v", [0.9])})

    write_las(
        pair_paths(raw, "15_9-F-12")[0],
        [3102.10200001, 3102.25439999, 3102.4068],
        {"GR": ("API", [90.0, 91.0, 92.0])},
    )
    write_las(
        pair_paths(raw, "15_9-F-12")[1],
        [3102.10200001, 3102.25439999, 3102.4068],
        {"KLOGH": ("mD", [10.0, 20.0, 30.0])},
    )
    write_las(
        raw / "Well_logs_pr_WELL" / "15_9-F-12" / INTERPRETATION / "geomod09"
        / "NO_15_9-F-12_KLOGH_NEW.las",
        [3102.102, 3102.2544, 3102.4068],
        {"KLOGH": ("mD", [999.0, 999.0, 999.0])},
    )

    # 15/9-F-11 T2 logs from 200.0 m; its interpretation starts deeper.
    write_las(
        pair_paths(raw, TECHNICAL_SIDETRACK[0])[0],
        [200.0, 200.1, 200.2, 4000.0],
        {"GR": ("API", [40.0, 41.0, 42.0, 43.0])},
    )
    write_las(pair_paths(raw, TECHNICAL_SIDETRACK[0])[1], [4000.0], {"PHIF": ("v/v", [0.2])})
    # The top-hole section lies inside T2's depth range with other values, and
    # has an all-NULL row at 200.2 m.
    write_las(
        pair_paths(raw, TOP_HOLE[0])[0],
        [200.0, 200.1, 200.2],
        {
            "GR": ("API", [30.0, 31.0, SENTINEL]),
            "ROP": ("m/hr", [12.0, SENTINEL, SENTINEL]),
        },
    )
    write_las(
        single_file_path(raw, "15_9-19 A"),
        [3666.5916, 3666.744, 3666.8964],
        {
            "BS": ("IN", [8.5, 8.5, SENTINEL]),
            "PHIF": ("V/V", [0.2, SENTINEL, SENTINEL]),
            "TEMP": ("DEGC", [112.7, 112.8, SENTINEL]),
        },
        well="NO_15/9-19_A",
    )
    write_las(
        single_file_path(raw, "15_9-19 B&BT2"),
        [3768.09, 3768.2424],
        {"PHIF": ("V/V", [0.25, 0.26]), "KLOGV": ("MD", [100.0, 200.0])},
    )
    write_las(
        single_file_path(raw, "15_9-19 S&SR"),
        [3549.7008, 3549.8532],
        {"DT": ("", [75.0, 76.0]), "SW": ("V/V", [1.0, SENTINEL])},
    )
    return raw


# GR: nine Wellbores; SW: the six plain pairs and 15/9-19 SR; PHIF:
# 15/9-F-1, 15/9-F-11, 15/9-19 A and 15/9-19 B; the rest one each, by
# mnemonic. A Wellbore counts once: VSH is in both files of 15/9-F-1, GR in
# both 15/9-F-11 sources (the Technical sidetrack and the top-hole section).
FIXTURE_COLUMNS = [
    "npd_wellbore_code", "source_wellbore", "depth_md",
    "GR", "SW", "PHIF",
    "BS", "COAL_FLAG", "DT", "KLOGH", "KLOGV", "RHOB", "ROP", "TEMP", "VSH",
]  # fmt: skip


def write_schema(path: Path, columns: list[dict]) -> None:
    path.write_text(
        json.dumps({"tables": {"petrophysical_interpretation": {"columns": columns}}})
    )


def fixture_schema() -> list[dict]:
    """The committed declarations of the fixture's columns, in the fixture's order.

    The schema.json a fixture build is checked against: the committed one
    declares Curves the fixture does not carry.
    """
    committed = json.loads(SCHEMA.read_text())["tables"]["petrophysical_interpretation"]
    by_name = {c["name"]: c for c in committed["columns"]}
    return [by_name[name] for name in FIXTURE_COLUMNS]
