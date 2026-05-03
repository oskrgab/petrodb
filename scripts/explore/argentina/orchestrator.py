"""Argentina explore-phase orchestrator.

Entry point for the EDA scripts that produce statistics and matplotlib
PNGs into `scripts/explore/argentina/output/`. The actual EDA logic
already lives alongside this module in earlier slices; this orchestrator
exists so all three phases share the same `run(...)` shape.
"""

from pathlib import Path


def run(db_path: Path | None = None) -> None:
    return None
