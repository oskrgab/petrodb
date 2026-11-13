"""Surface the Argentina dataset in the root ``README.md``.

One idempotent patch: an Argentina entry under the ``## Datasets``
section with a copy-pasteable DuckDB query example, bracketed by sentinel
HTML comments so re-running the export replaces the block in place rather
than appending a duplicate.

The Landing is not patched here: it is a prerendered site that reads the
Dataset metadata under ``site/data/argentina/`` (ADR-0010).
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Data host
# ---------------------------------------------------------------------------

# `BASE_URL` is the HF resolve base in CI (ADR-0005); local runs fall through
# to the dev Caddy host. `/argentina` matches this dataset's directory under
# `parquet/`. Used by the README's example query, which must name absolute
# HF URLs because the Landing (Cloudflare) does not carry the bytes (ADR-0005).
BASE_URL = os.environ.get("BASE_URL", "https://dev-petrodb.ocortez.com").rstrip("/")
ARGENTINA_BASE_URL = f"{BASE_URL}/argentina"

# ---------------------------------------------------------------------------
# Sentinel markers
# ---------------------------------------------------------------------------

README_BEGIN = "<!-- argentina:begin -->"
README_END = "<!-- argentina:end -->"

# ---------------------------------------------------------------------------
# Anchor (only used on the first run; subsequent runs find the sentinels)
# ---------------------------------------------------------------------------

# Insert the README blurb above this header so it sits between FORCE 2020
# and the Access Data section.
README_ANCHOR = "## Access Data"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def integrate(website_root: Path) -> None:
    """Idempotently inject the Argentina dataset entry into the root README.

    ``website_root`` is the repo root: the directory that contains
    ``README.md``. Re-running produces byte-identical output.
    """
    _patch_root_readme(Path(website_root) / "README.md")


# ---------------------------------------------------------------------------
# Root README
# ---------------------------------------------------------------------------


def _readme_payload() -> str:
    return f"""\

### Argentina Production Data
Monthly oil and gas production for ~85,418 wells in Argentina (2006–present),
sourced from the Secretaría de Energía public datasets:
- **wells.parquet** — static well master (~85K rows, Spanish column names)
- **well_operator_history.parquet** — slowly-changing operator transfers
- **well_events.parquet** — operational state transitions
- **monthly_production/** — hive-partitioned by `anio`, ~17.6M rows total

Aggregate 2023 production by basin, joining `wells` to the partitioned
monthly time series. The static host serves no directory listing, so the
partition files are discovered from the `_files.json` manifest rather than
globbed (ADR-0004):

```python
import json, urllib.request, duckdb

base = '{ARGENTINA_BASE_URL}/monthly_production/'
manifest = json.load(urllib.request.urlopen(base + '_files.json'))
urls = [base + p for p in manifest if p.startswith('anio=2023/')]

result = duckdb.sql(f\"\"\"
    SELECT w.cuenca,
           SUM(m.prod_pet) AS oil_m3,
           SUM(m.prod_gas) AS gas_mm3
    FROM '{ARGENTINA_BASE_URL}/wells.parquet' w
    JOIN read_parquet(?, hive_partitioning = true) m USING (idpozo)
    WHERE m.anio = 2023
    GROUP BY w.cuenca
    ORDER BY oil_m3 DESC
\"\"\", params=[urls]).df()
```

Full per-column English docs (Spanish column identifiers preserved), the
four-bucket rationale, and three more canonical query patterns live in
[`parquet/argentina/README.md`](parquet/argentina/README.md).

"""


def _patch_root_readme(path: Path) -> None:
    text = path.read_text()
    # Trailing blank line so the next markdown heading retains its required
    # blank-line separator.
    block = f"{README_BEGIN}\n{_readme_payload()}{README_END}\n\n"
    new_text = _replace_block_or_insert_before(
        text, README_BEGIN, README_END, README_ANCHOR, block
    )
    if new_text != text:
        path.write_text(new_text)


# ---------------------------------------------------------------------------
# Idempotent insert/replace helper
# ---------------------------------------------------------------------------


def _replace_block_or_insert_before(
    text: str, begin: str, end: str, anchor: str, block: str
) -> str:
    """Replace the region between ``begin`` and ``end`` with ``block`` if the
    sentinels exist; otherwise insert ``block`` immediately before ``anchor``.

    ``block`` must already include the ``begin`` and ``end`` markers and
    must end with the desired trailing whitespace before ``anchor``. On the
    replace branch we strip leading newlines from the suffix because they
    were inserted by the previous run as part of the block; the new block
    re-supplies them. This makes re-runs byte-identical to the first
    insertion.
    """
    if begin in text and end in text:
        prefix, _, rest = text.partition(begin)
        _, _, suffix = rest.partition(end)
        suffix = suffix.lstrip("\n")
        return prefix + block + suffix
    pos = text.index(anchor)
    return text[:pos] + block + text[pos:]
