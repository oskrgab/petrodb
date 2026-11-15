"""Read one DLIS file into an Arrow table: ``depth_md`` and one DOUBLE column per Curve.

DLIS is parsed with ``dlisio`` and its Curves go straight to Arrow, without
pandas, in the shape ``las_reader`` gives a LAS file, so the two join the same
way.

- The file must hold one logical file with one frame. Every Volve
  interpretation file does; a file with more would need a reviewed choice of
  frame, so it stops the build instead of being read by guess.
- The frame's first channel (the DLIS name for a sampled quantity) is its depth
  index. The Volve files write it in
  tenths of an inch (``0.1 in``) or in millimetres; it is converted to metres.
  Rounding happens where depths are joined, as for LAS.
- The absent value ``-999.25`` becomes NULL, as in LAS, and so does NaN.
- The Curves are 32-bit floats. Each value is widened to the double nearest
  its shortest decimal form (the float32 ``2.31`` becomes ``2.31``, not
  ``2.309999942779541``), which is the value as the file states it. The unit
  is not converted.
- Each Curve's field keeps the file's unit spelling as ``unit`` metadata, for
  the unit check (``units``).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
from dlisio import dlis

from scripts.transform.volve_logs.las_reader import DEPTH_COLUMN, SENTINEL
from scripts.transform.volve_logs.sources import SourceFileError
from scripts.transform.volve_logs.units import UNIT_METADATA_KEY

# Metres per unit of a depth index, as numerator / denominator: the index is
# multiplied exactly, then divided once.
INDEX_UNITS: dict[str, tuple[int, int]] = {
    "0.1 in": (254, 100_000),
    "mm": (1, 1_000),
}


def read_dlis(path: Path) -> pa.Table:
    """``depth_md`` in metres (unrounded) then each Curve under its mnemonic."""
    path = Path(path)
    if not path.is_file():
        raise SourceFileError(f"missing DLIS file: {path}")
    with dlis.load(str(path)) as logical_files:
        frames = [frame for logical_file in logical_files for frame in logical_file.frames]
        if len(logical_files) != 1 or len(frames) != 1:
            raise SourceFileError(
                f"{path}: holds {len(logical_files)} logical file(s) and "
                f"{len(frames)} frame(s); the pipeline reads a file with exactly one of each"
            )
        frame = frames[0]
        index, *channels = frame.channels
        samples = frame.curves()
        fields = [pa.field(DEPTH_COLUMN, pa.float64())]
        columns = [pa.array(_metres(path, index.units, samples[index.name]))]
        for channel in channels:
            values = samples[channel.name]
            if values.ndim != 1:
                raise SourceFileError(
                    f"{path}: Curve {channel.name} has {values.shape[1:]} values per "
                    "depth; the pipeline reads one value per depth"
                )
            values = _as_stated(values)
            fields.append(
                pa.field(
                    channel.name,
                    pa.float64(),
                    metadata={UNIT_METADATA_KEY: channel.units or ""},
                )
            )
            columns.append(pa.array(values, mask=np.isnan(values) | (values == SENTINEL)))
    return pa.Table.from_arrays(columns, schema=pa.schema(fields))


def _metres(path: Path, unit: str | None, index: np.ndarray) -> np.ndarray:
    if unit not in INDEX_UNITS:
        raise SourceFileError(
            f"{path}: depth index is in {unit!r}; the pipeline converts "
            f"{', '.join(repr(u) for u in INDEX_UNITS)} to metres"
        )
    numerator, denominator = INDEX_UNITS[unit]
    return index.astype(np.float64) * numerator / denominator


def _as_stated(values: np.ndarray) -> np.ndarray:
    """``values`` as doubles; a float32 becomes the double of its shortest decimal form."""
    if values.dtype == np.float32:
        return values.astype(str).astype(np.float64)
    return values.astype(np.float64)
