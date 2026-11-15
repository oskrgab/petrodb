# Local raw directories

Each folder here is a **plain download of one Raw repo** (ADR-0011): the same
files at the same paths, nothing added or renamed. The folders are gitignored;
only this README and the pins are committed. A local build reads a folder here,
and CI reads the same Raw repo at the same pin, so both builds see the same
bytes.

| Folder | Raw repo | Pin |
| --- | --- | --- |
| `volve/` | [`oskrgab/petrodb-raw-volve`](https://huggingface.co/datasets/oskrgab/petrodb-raw-volve) | `volve.pin` |

## The pin

`volve.pin` holds the Raw repo commit the Volve log pipeline reads: one full
40-character commit hash and nothing else. It is the only place the pin is
recorded. The pipeline reads it with `scripts.raw_repo.volve.pin.read_pin()`
and the deploy workflow reads the same file. It is empty until the Raw repo is
filled. Moving it is a reviewed change.

## `volve/`

```text
data/raw/volve/
├── README.md                      the Raw repo's card
├── LICENSE.md                     Volve licence note and attribution
├── Well_logs_pr_WELL/             the operator's by-wellbore log tree
│   ├── VOLVE_INVENTORY.xlsx
│   ├── 15_9-F-1/                  one folder per wellbore, upstream name
│   │   ├── 01.MUD_LOG/            one folder per log type, upstream numbering
│   │   ├── 04.COMPOSITE/
│   │   ├── 05.PETROPHYSICAL INTERPRETATION/
│   │   └── ...
│   ├── 15_9-19 B&BT2/
│   └── ...
└── register/                      wellbore register snapshot (NLOD)
    ├── LICENSE.md
    ├── download_date.txt
    ├── wellbore_development_all.csv
    └── wellbore_exploration_all.csv
```

Names are upstream's, with spaces and `&`; quote them in a shell. The Raw
repo's README lists the few changes from the operator's layout. The files
originate from Equinor's Volve data sharing page,
<https://www.equinor.com/energy/volve-data-sharing>.

### Download it

From the repo root, with the [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli)
(`uvx --from huggingface_hub hf ...` works without installing it):

```bash
# At the pinned commit, everything (about 16 GB)
hf download oskrgab/petrodb-raw-volve --repo-type dataset \
  --revision "$(cat data/raw/volve.pin)" --local-dir data/raw/volve

# Only what the petrophysical interpretation build reads
hf download oskrgab/petrodb-raw-volve --repo-type dataset \
  --revision "$(cat data/raw/volve.pin)" --local-dir data/raw/volve \
  --include "Well_logs_pr_WELL/*/05.PETROPHYSICAL INTERPRETATION/*" --include "register/*"
```

While `volve.pin` is empty, leave out `--revision` to read the latest commit.

### Fill the Raw repo (maintainer)

The commands that fill the Raw repo live in `scripts/raw_repo/volve/`. The
source directory is a local copy of the operator's release that keeps upstream
paths (`Well_logs_pr_WELL/`, and `Well_logs/` for the by-type tree).

```bash
# Download the wellbore register snapshot into SOURCE_DIR/register/
uv run python -m scripts.raw_repo.volve fetch-register SOURCE_DIR

# Print the upload plan (source, tab, Raw repo path), totals and adjustments; offline
uv run python -m scripts.raw_repo.volve plan SOURCE_DIR

# Upload a few files as a trial, then everything; rerun to resume
uv run python -m scripts.raw_repo.volve upload SOURCE_DIR --include "Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/*"
uv run python -m scripts.raw_repo.volve upload SOURCE_DIR
```

`fetch-register` with no directory writes to `data/raw/volve/register/`, which
refreshes the register snapshot of a local raw directory.
