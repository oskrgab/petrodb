"""Read one LAS file into an Arrow table: ``depth_md`` and one DOUBLE column per Curve.

LAS is parsed with ``lasio`` and its columns go straight to Arrow, without
pandas. The sentinel ``-999.25`` becomes NULL whatever the file's ``NULL``
header says, and so does any value ``lasio`` already turned into NaN. Depth is
kept at the source samples; rounding happens where depths are joined.
"""

from __future__ import annotations

from pathlib import Path

import lasio
import numpy as np
import pyarrow as pa

SENTINEL = -999.25
DEPTH_COLUMN = "depth_md"


class LasSourceError(Exception):
    """A LAS file the pipeline needs is missing or cannot be used."""


def read_las(path: Path) -> pa.Table:
    """``depth_md`` (as the source wrote it) then each Curve under its mnemonic."""
    path = Path(path)
    if not path.is_file():
        raise LasSourceError(f"missing LAS file: {path}")
    # null_policy="none": sentinels are masked below, the same way in every file.
    las = lasio.read(str(path), null_policy="none", engine="normal")
    index = las.curves[0]
    if index.unit.upper() != "M":
        raise LasSourceError(
            f"{path}: depth index {index.mnemonic!r} is in {index.unit!r}, not metres"
        )
    columns = {DEPTH_COLUMN: pa.array(np.asarray(index.data, dtype=np.float64))}
    for curve in las.curves[1:]:
        values = np.asarray(curve.data, dtype=np.float64)
        columns[curve.mnemonic] = pa.array(
            values, mask=np.isnan(values) | (values == SENTINEL)
        )
    return pa.table(columns)
