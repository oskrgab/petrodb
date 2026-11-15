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
and the deploy workflow reads the same file. It names the commit that holds the
full upload of the upload plan. Moving it is a reviewed change.

## `volve/`

```text
data/raw/volve/
├── README.md                      the Raw repo's card
├── LICENSE.md                     Volve licence note and attribution
├── Well_logs_pr_WELL/             the operator's by-wellbore log tree
│   ├── VOLVE_INVENTORY.xlsx
│   ├── 15_9-F-1/                  one folder per upstream wellbore name
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

# Only the files the log pipeline reads (in bash, for mapfile)
mapfile -t files < <(uv run python -m scripts.run_pipeline.volve_logs --list-raw-files)
hf download oskrgab/petrodb-raw-volve "${files[@]}" --repo-type dataset \
  --revision "$(cat data/raw/volve.pin)" --local-dir data/raw/volve
```

`--list-raw-files` prints those files one per line, as paths within the Raw
repo, and builds nothing.

### Build the log tables

From the repo root, once `data/raw/volve/` is downloaded:

```bash
uv run python -m scripts.run_pipeline.volve_logs
```

It reads `data/raw/volve/` and writes
`parquet/volve/petrophysical_interpretation.parquet` and its Curve catalog,
`parquet/volve/log_curves.parquet`, both gitignored. It checks them against
the committed `parquet/volve/wells.parquet` and `parquet/volve/schema.json`,
so it writes beside them: the build fails if the table differs from
`schema.json` in a column name, order, type or nullability, or if it is not a
single row group, and if the catalog disagrees with the table: one row per
Curve with data for each `source_wellbore`, with the table's depth range and
sample count. Another raw or output directory goes as arguments:
`uv run python -m scripts.run_pipeline.volve_logs RAW_DIR OUTPUT_DIR`.

So far it reads the LAS input and output pairs of eight Wellbores and of the
Technical sidetrack 15/9-F-11 T2, the input file of the 15/9-F-11 top-hole
section, which has no output file, and the DLIS input and output pairs of
eight more Wellbores, from
`Well_logs_pr_WELL/<wellbore>/05.PETROPHYSICAL INTERPRETATION/`. A DLIS
file must hold one frame, its depth index in tenths of an inch or in
millimetres; the build converts it to metres, and stops on any other file. The folder
names the source, through the mapping in
`scripts/transform/volve_logs/sources.py`: the Technical sidetrack's rows take the
`npd_wellbore_code` of its parent, 15/9-F-11, and keep `15/9-F-11 T2` in
`source_wellbore`. Each Curve's unit spelling must be one the unit table in
`scripts/transform/volve_logs/units.py` maps to the unit documented for its
column; the build stops on any other, naming the file, the mnemonic and the
spelling, and a new spelling is added there by review. Both files are checked
before either is moved into place; a failed check leaves no new file.

### In CI

The deploy workflow (`.github/workflows/deploy-cloudflare-pages.yml`) runs the
same two commands, the download above and the build, on every `main` or
`stage` deploy whose cache misses, then uploads the tables to the matching
revision of `oskrgab/petrodb`. It downloads with a read token, the
`HF_RAW_READ_TOKEN` secret. The cache is keyed on the pin, the pipeline
sources, the committed `wells.parquet` and `schema.json`, and `uv.lock`; a
deploy that changes none of them restores the tables without rebuilding. A
failed check stops the deploy before anything is uploaded.

### Fill the Raw repo (maintainer)

The commands that fill the Raw repo live in `scripts/raw_repo/volve/`.
`SOURCE_DIR` is a local copy of the operator's release that keeps upstream
paths (`Well_logs_pr_WELL/`, and `Well_logs/` for the by-type tree); it is only
read. The register snapshot is fetched into the local raw directory,
`data/raw/volve/register/`, and the plan takes it from there.

```bash
# Download the wellbore register snapshot into data/raw/volve/register/
uv run python -m scripts.raw_repo.volve fetch-register

# Print the upload plan (source, tab, Raw repo path), totals and adjustments; offline
uv run python -m scripts.raw_repo.volve plan SOURCE_DIR

# Upload a few files as a trial, then everything; rerun to resume
uv run python -m scripts.raw_repo.volve upload SOURCE_DIR --include "Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/*"
uv run python -m scripts.raw_repo.volve upload SOURCE_DIR
```

Before it uploads, `upload` adds one rule to the Raw repo's `.gitattributes`,
if it is missing, so that every file under `Well_logs_pr_WELL/` goes to Xet
storage: the Hub otherwise takes a few small binary files for text and refuses
the commit. `.gitattributes` is the Hub's own file, not part of the plan.

`fetch-register`, `plan` and `upload` take another local raw directory as
`RAW_DIR` (`fetch-register RAW_DIR`, `--raw-dir RAW_DIR`).
