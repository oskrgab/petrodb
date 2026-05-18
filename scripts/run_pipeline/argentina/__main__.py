"""One-shot runner for the Argentina dataset transform -> export pipeline.

Invoke from the repo root:

    uv run python -m scripts.run_pipeline.argentina
"""

from pathlib import Path

from scripts.export.argentina import orchestrator as export_orch
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
        website_root=REPO_ROOT,
    )


if __name__ == "__main__":
    main()
