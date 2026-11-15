"""Synthetic LAS and DLIS files laid out like the Volve Raw repo, written at test time.

Every file is generated into a temporary directory, LAS with ``lasio`` and
DLIS with ``dliswriter``; no real log file and no network is needed. The tree
holds, under the upstream folder names, one LAS pair for each of the eight
Wellbores the petrophysical interpretation reads as LAS pairs, the LAS pair of
the Technical sidetrack 15/9-F-11 T2, the input file of the 15/9-F-11 top-hole
section, and one DLIS pair for each of the eight Wellbores read as DLIS
pairs. Beside them sits a geomodel permeability export the build must not
read.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import lasio
import numpy as np
from dliswriter import DLISFile

# dliswriter warns on every unit outside the RP66 list; the Volve files use
# such spellings ("0.1 in", "API", "UNKNOWN"), and so do the fixtures.
logging.getLogger("dliswriter").setLevel(logging.ERROR)

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
TECHNICAL_SIDETRACK = ("15_9-F-11 T2", "15/9-F-11 T2", 7078)
# The 15/9-F-11 top-hole section: an input file and no output file.
TOP_HOLE = ("15_9-F-11", "15/9-F-11", 7078)

# The Wellbores whose interpretation exists only as DLIS.
DLIS_WELLBORES = {
    "15_9-F-4": ("15/9-F-4", 5693),
    "15_9-F-5": ("15/9-F-5", 5769),
    "15_9-F-10": ("15/9-F-10", 6099),
    "15_9-F-14": ("15/9-F-14", 5351),
    "15_9-F-15": ("15/9-F-15", 6184),
    "15_9-F-15 A": ("15/9-F-15 A", 5785),
    "15_9-F-15 B": ("15/9-F-15 B", 6046),
    "15_9-F-15 C": ("15/9-F-15 C", 5794),
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


def write_dlis(
    path: Path,
    index: list[float],
    curves: Curves,
    index_unit: str = "0.1 in",
    frames: int = 1,
) -> Path:
    """A DLIS file with one logical file and a DEPTH-indexed frame of the given Curves.

    The index is written as the Volve files write it: 32-bit integers in
    ``index_unit`` (tenths of an inch, or millimetres); Curves are 32-bit
    floats with ``-999.25`` for an absent value. ``frames`` > 1 repeats the
    frame under another name, as a file with several frames would hold.
    """
    dlis = DLISFile()
    logical_file = dlis.add_logical_file()
    logical_file.add_origin("ORIGIN", well_name="SOME OTHER NAME")
    data = {"DEPTH": np.asarray(index, dtype=np.int32)}
    data |= {name: np.asarray(values, dtype=np.float32) for name, (_, values) in curves.items()}
    for frame in range(frames):
        suffix = "" if frame == 0 else f"_{frame}"
        channels = [
            logical_file.add_channel(f"DEPTH{suffix}", data=data["DEPTH"], units=index_unit)
        ] + [
            logical_file.add_channel(f"{name}{suffix}", data=data[name], units=unit or None)
            for name, (unit, _) in curves.items()
        ]
        logical_file.add_frame(str(frame), channels=channels, index_type="BOREHOLE-DEPTH")
    path.parent.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        # dliswriter times the write and averages an empty list of timings.
        warnings.simplefilter("ignore", RuntimeWarning)
        # The default output buffer is 4 GB, allocated on every write.
        dlis.write(path, output_chunk_size=2**16)
    return path


def pair_paths(raw: Path, folder: str, extension: str = "LAS") -> tuple[Path, Path]:
    """The input and output file of ``folder``'s interpretation."""
    base = raw / "Well_logs_pr_WELL" / folder / INTERPRETATION
    return (
        base / f"WLC_PETRO_COMPUTED_INPUT_1.{extension}",
        base / f"WLC_PETRO_COMPUTED_OUTPUT_1.{extension}",
    )


def dlis_pair_paths(raw: Path, folder: str) -> tuple[Path, Path]:
    return pair_paths(raw, folder, "DLIS")


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
    build_dlis_pairs(raw)
    return raw


def build_dlis_pairs(raw: Path) -> None:
    """One DLIS pair per DLIS Wellbore. 15/9-F-10 carries the interesting cases.

    Indexes are in tenths of an inch (60 = 0.1524 m) unless said otherwise.

    - 15/9-F-10: input at 4850.13 .. 4850.4348 m; the output pads the well
      from 0 m with all-NULL samples down to the same three depths. RHOB is in
      both files, spelled ``G/CC`` and ``G/C3``, and equal.
    - 15/9-F-15: the input starts at 0 m with two all-NULL samples.
    - 15/9-F-15 B: both indexes in millimetres.
    - The rest: two input depths, an Interpreted curve at the second.
    """
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-10")[0],
        [1909500, 1909560, 1909620],
        {
            "GR": ("GAPI", [80.5, 81.5, 82.5]),
            "RHOB": ("G/CC", [2.31, 2.32, SENTINEL]),
        },
    )
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-10")[1],
        [0, 60, 120, 1909500, 1909560, 1909620],
        {
            "PHIF": ("V/V", [SENTINEL, SENTINEL, SENTINEL, 0.21, 0.22, 0.23]),
            "RHOB": ("G/C3", [SENTINEL, SENTINEL, SENTINEL, 2.31, 2.32, SENTINEL]),
        },
    )
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-15")[0],
        [0, 60, 1000000],
        {"GR": ("GAPI", [SENTINEL, SENTINEL, 70.0])},
    )
    write_dlis(dlis_pair_paths(raw, "15_9-F-15")[1], [1000000], {"SW": ("V/V", [0.8])})
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-15 B")[0],
        [3500000, 3500152],
        {"GR": ("GAPI", [60.0, 61.0])},
        index_unit="mm",
    )
    write_dlis(
        dlis_pair_paths(raw, "15_9-F-15 B")[1],
        [3500152],
        {"SW": ("V/V", [0.7])},
        index_unit="mm",
    )
    for folder in DLIS_WELLBORES:
        if folder in ("15_9-F-10", "15_9-F-15", "15_9-F-15 B"):
            continue
        write_dlis(dlis_pair_paths(raw, folder)[0], [1000000, 1000060], {"GR": ("API", [80.0, 81.0])})
        write_dlis(dlis_pair_paths(raw, folder)[1], [1000060], {"SW": ("v/v_decimal", [0.9])})
