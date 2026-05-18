"""One-shot runner for the Petrobras 3W dataset transform -> export pipeline.

Invoke from the repo root:

    uv run python -m scripts.run_pipeline.petrobras_3w

The transform phase shallow-clones the pinned upstream tag into
``data/petrobras_3w/`` on first run (~1.74 GB); subsequent runs reuse it.
"""

from pathlib import Path

from scripts.export.petrobras_3w import orchestrator as export_orch
from scripts.transform.petrobras_3w import orchestrator as transform_orch

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "database" / "petrobras_3w.duckdb"
STAGING_DIR = REPO_ROOT / "data" / "petrobras_3w"
OUTPUT_DIR = REPO_ROOT / "parquet" / "petrobras_3w"


def main() -> None:
    dataset_ini = transform_orch.run(db_path=DB_PATH, staging_dir=STAGING_DIR)
    export_orch.run(
        db_path=DB_PATH,
        output_dir=OUTPUT_DIR,
        dataset_ini=dataset_ini,
        staging_dir=STAGING_DIR,
        website_root=REPO_ROOT,
    )


if __name__ == "__main__":
    main()
