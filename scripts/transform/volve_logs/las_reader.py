"""Read one LAS file into an Arrow table: ``depth_md`` and one DOUBLE column per Curve.

LAS is parsed with ``lasio`` and its columns go straight to Arrow, without
pandas. The sentinel ``-999.25`` becomes NULL whatever the file's ``NULL``
header says, and so does any value ``lasio`` already turned into NaN. Depth is
kept at the source samples; rounding happens where depths are joined. Each
Curve's field keeps the file's unit spelling as ``unit`` metadata, for the
unit check (``units``).
"""

from __future__ import annotations

from pathlib import Path

import lasio
import numpy as np
import pyarrow as pa

from scripts.transform.volve_logs.sources import SourceFileError
from scripts.transform.volve_logs.units import UNIT_METADATA_KEY

SENTINEL = -999.25
DEPTH_COLUMN = "depth_md"


def read_las(path: Path) -> pa.Table:
    """``depth_md`` (as the source wrote it) then each Curve under its mnemonic."""
    path = Path(path)
    if not path.is_file():
        raise SourceFileError(f"missing LAS file: {path}")
    # null_policy="none": sentinels are masked below, the same way in every file.
    las = lasio.read(str(path), null_policy="none", engine="normal")
    index = las.curves[0]
    if index.unit.upper() != "M":
        raise SourceFileError(
            f"{path}: depth index {index.mnemonic!r} is in {index.unit!r}, not metres"
        )
    fields = [pa.field(DEPTH_COLUMN, pa.float64())]
    columns = [pa.array(np.asarray(index.data, dtype=np.float64))]
    for curve in las.curves[1:]:
        values = np.asarray(curve.data, dtype=np.float64)
        fields.append(
            pa.field(curve.mnemonic, pa.float64(), metadata={UNIT_METADATA_KEY: curve.unit})
        )
        columns.append(pa.array(values, mask=np.isnan(values) | (values == SENTINEL)))
    return pa.Table.from_arrays(columns, schema=pa.schema(fields))
