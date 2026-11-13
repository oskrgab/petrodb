"""One-shot runner for the Argentina dataset transform -> export pipeline.

Invoke from the repo root:

    uv run python -m scripts.run_pipeline.argentina

The last step regenerates the Argentina Glances, facts and file listing under
``site/data/argentina/`` so the Landing never drifts from the export.
"""

from pathlib import Path

from scripts.export.argentina import orchestrator as export_orch
from scripts.site import glances
from scripts.transform.argentina import orchestrator as transform_orch

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "database" / "argentina.duckdb"
CSV_DIR = REPO_ROOT / "data" / "Argentina"
OUTPUT_DIR = REPO_ROOT / "parquet" / "argentina"


def main() -> None:
    transform_orch.run(db_path=DB_PATH, csv_dir=CSV_DIR)
    export_orch.run(
        db_path=DB_PATH,
        output_dir=OUTPUT_DIR,
        repo_root=REPO_ROOT,
    )
    glances.write("argentina")


if __name__ == "__main__":
    main()
