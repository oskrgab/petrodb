---
license: other
license_name: equinor-open-data-licence
license_link: LICENSE.md
pretty_name: PetroDB Raw - Volve
viewer: false
tags:
  - petroleum
  - well-logs
  - las
  - dlis
  - volve
---

# PetroDB Raw: Volve

The raw source files behind the Volve well-log tables of
[PetroDB](https://petrodb.ocortez.com/), kept as upstream lays them out.

This is a **Raw repo**: it holds upstream files, not tables. The PetroDB
pipeline reads it at a pinned commit, builds Parquet tables from it and
publishes them in the [`oskrgab/petrodb`](https://huggingface.co/datasets/oskrgab/petrodb)
dataset, under `volve/`. Query those tables; download this repo to rerun the
build or to read the original files.

## Source

The files are the well-log part of the Volve field data released by Equinor.
The official source is Equinor's Volve data sharing page:
<https://www.equinor.com/energy/volve-data-sharing>.

## Licence and attribution

© Equinor and the former Volve licence partners, ExxonMobil Exploration &
Production Norway AS and Bayerngas Norge AS. The Volve data is licensed under
the Equinor Open Data Licence: it may be shared and adapted with attribution
and may not be sold. See [`LICENSE.md`](LICENSE.md) for the attribution, a
summary of the terms and the link to the official text.

The wellbore register snapshot in `register/` is published by the Norwegian
Offshore Directorate under the Norwegian Licence for Open Government Data
(NLOD); see [`register/LICENSE.md`](register/LICENSE.md).

Raw file headers are published as they are, including the names of the
companies that acquired the logs.

## Layout

```text
README.md                      this card
LICENSE.md                     the Volve licence note and attribution
Well_logs_pr_WELL/             the operator's by-wellbore log tree, whole
  VOLVE_INVENTORY.xlsx
  15_9-F-1/                    one folder per upstream wellbore name
    01.MUD_LOG/                one folder per log type, numbered as upstream numbers it
    02.LWD_EWL/
    04.COMPOSITE/
    05.PETROPHYSICAL INTERPRETATION/
    ...
  15_9-19 B&BT2/
  ...
register/                      the public wellbore register snapshot
  LICENSE.md                   its licence note (NLOD)
  download_date.txt
  wellbore_development_all.csv
  wellbore_exploration_all.csv
```

File and folder names are upstream's, unchanged, including names with spaces
and `&` (`15_9-19 B&BT2`, `05.PETROPHYSICAL INTERPRETATION`). Quote them in a
shell, and percent-encode them in a URL.

## Changes from upstream

Upstream ships the same log files twice: in a by-wellbore tree
(`Well_logs_pr_WELL`) and in a by-type tree (`Well_logs`). This repo holds the
by-wellbore tree, with three adjustments:

1. **Operating-system junk files are left out**: thumbnail caches
   (`Thumbs.db`), folder metadata and office lock files (`~$...`). They are not
   data.
2. **Five biostratigraphy files are added.** They exist only in the by-type
   tree, so they are added at the path they would have in the by-wellbore tree:
   - `Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/001.tif`
   - `Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/002.tif`
   - `Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/003.tif`
   - `Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/004.tif`
   - `Well_logs_pr_WELL/15_9-19 B&BT2/12.BIOSTRAT/15-9-19b-bio.pdf`
3. **The rest of the by-type tree is left out.** It duplicates the by-wellbore
   tree.

Nothing else is renamed, moved or edited. The upload script in the PetroDB
repository (`scripts/raw_repo/volve/`) builds the upload plan and prints every
file, its path here and each of these adjustments.

## Download

```bash
# Everything (about 16 GB)
hf download oskrgab/petrodb-raw-volve --repo-type dataset --local-dir data/raw/volve

# Only the petrophysical interpretation folders and the register
hf download oskrgab/petrodb-raw-volve --repo-type dataset --local-dir data/raw/volve \
  --include "Well_logs_pr_WELL/*/05.PETROPHYSICAL INTERPRETATION/*" --include "register/*"
```

Add `--revision <commit>` to read the commit a PetroDB build is pinned to.
