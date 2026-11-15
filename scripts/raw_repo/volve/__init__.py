"""Fill the Volve Raw repo, oskrgab/petrodb-raw-volve (ADR-0011).

Paths in this repo that the Raw repo scripts share.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Local raw directories: plain downloads of the Raw repos, and their pins
# (data/raw/README.md).
LOCAL_RAW_ROOT = REPO_ROOT / "data" / "raw"
LOCAL_RAW_DIR = LOCAL_RAW_ROOT / "volve"
PIN_FILE = LOCAL_RAW_ROOT / "volve.pin"

# The Raw repo's own README and licence notes, at their paths in the Raw repo.
RAW_REPO_DOCS_DIR = REPO_ROOT / "hf" / "petrodb-raw-volve"
