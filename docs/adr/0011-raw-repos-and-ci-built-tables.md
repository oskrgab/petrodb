# Build tables in CI from a Raw repo; publish the Parquet to Hugging Face only

**Status:** accepted. Piloted by the Volve log tables; the other Datasets keep their current build until they migrate.

## Context

Volve, FORCE 2020 and Argentina are built on a maintainer's machine and their Parquet is committed to git; the deploy workflow then copies the committed bytes to Hugging Face (ADR-0005). The source files those builds read are not published anywhere by petrodb, so nobody else can rerun a build, and the repo grows with every regenerated table. Petrobras 3W already works differently: its tree is gitignored and rebuilt in CI from a pinned upstream tag (ADR-0002), which is possible because its upstream is a public git repo.

The Volve well logs have no such upstream. The operator distributes them through a portal that needs an account and a manual download, the log tree is 16 GB, and the Parquet built from it would be binary churn in git. petrodb's purpose is also wider than hosting tables: it should show the whole path from raw files to storage that is efficient to query, and that path is invisible while the raw files sit on one machine.

## Decision

Each Dataset may have a **Raw repo**: a public Hugging Face dataset repo, named `petrodb-raw-<dataset>` under the same namespace as the published Dataset (ADR-0009), holding that Dataset's upstream source files with their bytes unmodified and laid out as upstream lays them out, except for adjustments to the layout that its README records. A pipeline reads its Raw repo at a pinned commit recorded in this repo, builds the tables in CI, and uploads the Parquet to the published Dataset. The Parquet is never committed.

This repo holds everything except the bytes: the pipelines, the workflows, the script that fills each Raw repo, the pin, and the schema documents. A local build reads a gitignored directory that is a plain download of the Raw repo, so a local run and a CI run read the same tree.

The first Raw repo is `oskrgab/petrodb-raw-volve`, filled by hand once because its upstream cannot be scripted. A Dataset whose upstream can be scripted fills its Raw repo from a workflow in this repo.

## Considered alternatives

- **Build locally and commit the Parquet**, as Volve production, FORCE 2020 and Argentina do today. Rejected for the logs: the build cannot be reproduced without the raw files, and each rebuild adds binary history to git.
- **One Raw repo for every Dataset.** Rejected: Datasets differ in licence, in size and in how they are refreshed (a hand upload for Volve, a scheduled scrape for Argentina). One repo per Dataset keeps each licence note, each pin and each refresh workflow separate.
- **Fetch from the operator's portal or from a private file share in CI.** Rejected: the portal cannot be scripted, and a private share is a secret that makes the build unreproducible for everyone else.
- **Keep the raw files in the published Dataset repo.** Rejected: consumers query that repo, and the deploy upload deletes whatever is absent from the CI checkout.
- **A second GitHub repo per Raw repo for its upload scripts.** Rejected: the scripts and workflows fit in this repo, next to the pipelines that depend on them.

## Consequences

- Moving the pin is a reviewed change, as with the 3W tag (ADR-0002). The CI cache key includes the pin and the pipeline sources.
- The deploy upload deletes remote Parquet that is absent from the checkout, so a CI-built table must be built or restored from cache before every upload, as the 3W tree is.
- Schema documents stay committed for CI-built tables. The build fails when its output does not match them, because nothing else would catch the drift.
- A Raw repo republishes upstream files, so it carries its own licence note and attribution, and raw file headers are published as they are.
- Hugging Face gives public repos storage on a best-effort basis. The Volve log tree is 16 GB; the full Volve release is 66 GB and may need a storage grant or a paid plan.
- CI downloads only the files a pipeline reads, with the `HF_TOKEN` secret the upload already uses, since anonymous downloads are rate-limited per IP.
- Issue #45 (scheduled Argentina refresh, published to Hugging Face only) is the same pattern with a scripted upstream, and should adopt a Raw repo when it is built.
