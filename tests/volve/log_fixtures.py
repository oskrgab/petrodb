"""Synthetic LAS files laid out like the Volve Raw repo, written at test time.

Every file is generated with ``lasio`` into a temporary directory; no real log
file and no network is needed. The tree holds one LAS pair for each of the
eight Wellbores the petrophysical interpretation reads as LAS pairs, under the
upstream folder names, plus a geomodel permeability export the build must not
read, the LAS pair of the Technical sidetrack 15/9-F-11 T2 and the input-only
15/9-F-11 top-hole section.
"""

from __future__ import annotations

from pathlib import Path

import lasio

SENTINEL = -999.25
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
SIDETRACK = ("15_9-F-11 T2", "15/9-F-11 T2", 7078)
# The 15/9-F-11 top-hole section: an input file and no output file.
TOP_HOLE = ("15_9-F-11", "15/9-F-11", 7078)

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
        pair_paths(raw, SIDETRACK[0])[0],
        [200.0, 200.1, 200.2, 4000.0],
        {"GR": ("API", [40.0, 41.0, 42.0, 43.0])},
    )
    write_las(pair_paths(raw, SIDETRACK[0])[1], [4000.0], {"PHIF": ("v/v", [0.2])})
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
    return raw
