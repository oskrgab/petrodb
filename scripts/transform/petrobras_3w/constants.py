"""Pinning + upstream identity for the Petrobras 3W pipeline.

The pin separates two upstream version namespaces (see ADR-0002):

- `PIN_GIT_TAG` — what `git clone --branch` accepts. Bytes-stable.
- `PIN_DATASET_VERSION` — the data-shape semver from `dataset/README.md`.
  This is what consumers care about; the git tag is the mechanism that
  delivers it byte-stably.

Both values are emitted in the validation log so a consumer can verify
which upstream snapshot backs the published data.
"""

import os

UPSTREAM_REPO_URL = "https://github.com/petrobras/3W.git"
PIN_GIT_TAG = "v.1.70.0"
PIN_DATASET_VERSION = "2.0.0"

UPSTREAM_DATASET_INI_RELPATH = "dataset/dataset.ini"

# Host where the petrodb site is served, sourced from `BASE_URL` so CI can
# select prod vs stage. Local runs fall through to the dev Caddy host. The
# `/petrobras_3w` suffix below matches this dataset's directory under
# `parquet/`, so the host alone is what callers configure.
BASE_URL = os.environ.get("BASE_URL", "https://dev-petrodb.ocortez.com").rstrip("/")

# Full public base for this dataset's parquets. The Observations hive partition
# by `event_class` is fixed by ADR-0001, so every Instance's published URL is
# fully determined here — `instances.parquet` materialises this as `source_url`
# even before the Observations files exist.
PUBLIC_BASE_URL = f"{BASE_URL}/petrobras_3w"
