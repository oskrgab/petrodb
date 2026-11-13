"""Surface the Petrobras 3W dataset in the root ``README.md``.

One idempotent patch: a Petrobras 3W entry under the ``## Datasets``
section with a copy-pasteable DuckDB query example, bracketed by sentinel
HTML comments so re-running the export replaces the block in place rather
than appending a duplicate. The same mechanism as the Argentina integrator.

The Landing is not patched here: it is a prerendered site that reads the
Dataset metadata under ``site/data/petrobras_3w/`` (ADR-0010).
"""

from __future__ import annotations

from pathlib import Path

from scripts.transform.petrobras_3w.constants import (
    PIN_DATASET_VERSION,
    PIN_GIT_TAG,
    PUBLIC_BASE_URL,
    UPSTREAM_REPO_URL,
)

README_BEGIN = "<!-- petrobras_3w:begin -->"
README_END = "<!-- petrobras_3w:end -->"

# Insert the README blurb above this header so it sits between the
# Argentina entry and the Access Data section.
README_ANCHOR = "## Access Data"


def integrate(repo_root: Path) -> None:
    """Idempotently inject the Petrobras 3W dataset entry into the root README.

    ``repo_root`` is the repo root containing ``README.md``. Re-running
    produces byte-identical output.
    """
    _patch_root_readme(Path(repo_root) / "README.md")


def _readme_payload() -> str:
    return f"""\

### Petrobras 3W Dataset
Labelled 1-Hz sensor-data windows from the Petrobras 3W dataset, sliced
into per-Instance Parquet files. Pinned at upstream git tag `{PIN_GIT_TAG}`
(dataset version `{PIN_DATASET_VERSION}`). This release publishes the
event-class lookup, the real-Well master, the full Instance catalog, and
the per-Instance Observations time-series (hive-partitioned by event class).

Measure the labelled-data balance across the corpus from the catalog alone
(no Observations scan needed):

```python
import duckdb

base = '{PUBLIC_BASE_URL}'
result = duckdb.sql(f\"\"\"
    SELECT
        et.event_class,
        et.description,
        COUNT(*)             AS n_instances,
        SUM(i.n_rows)        AS n_observations
    FROM '{{base}}/instances.parquet' i
    JOIN '{{base}}/event_types.parquet' et
        ON et.event_class = i.event_class
    GROUP BY et.event_class, et.description
    ORDER BY et.event_class
\"\"\").df()
```

Full per-column English docs (including the 27-sensor glossary mirrored
from upstream `dataset.ini`) live in
[`parquet/petrobras_3w/README.md`](parquet/petrobras_3w/README.md). Upstream
source: <{UPSTREAM_REPO_URL}> (CC BY 4.0).

"""


def _patch_root_readme(path: Path) -> None:
    text = path.read_text()
    block = f"{README_BEGIN}\n{_readme_payload()}{README_END}\n\n"
    new_text = _replace_block_or_insert_before(
        text, README_BEGIN, README_END, README_ANCHOR, block
    )
    if new_text != text:
        path.write_text(new_text)


def _replace_block_or_insert_before(
    text: str, begin: str, end: str, anchor: str, block: str
) -> str:
    """Replace the region between ``begin`` and ``end`` with ``block`` if
    the sentinels exist; otherwise insert ``block`` immediately before
    ``anchor``. Same mechanism as the Argentina integrator.
    """
    if begin in text and end in text:
        prefix, _, rest = text.partition(begin)
        _, _, suffix = rest.partition(end)
        suffix = suffix.lstrip("\n")
        return prefix + block + suffix
    pos = text.index(anchor)
    return text[:pos] + block + text[pos:]
