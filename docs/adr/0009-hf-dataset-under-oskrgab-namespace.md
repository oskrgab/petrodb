# Host the Hugging Face dataset under the `oskrgab` namespace

**Status:** accepted — amends [ADR-0005](0005-host-parquet-on-huggingface.md)

## Context

ADR-0005 put the parquet bytes in a Hugging Face dataset repo owned by the SumpaLabs org, `sumpalabs/petrodb`. [ADR-0007](0007-landing-hosts-independently-of-sumpalabs-apex.md) later ruled that petrodb's public hosting is independent of SumpaLabs — "no host inside the SumpaLabs namespace" — and moved the landing back to `petrodb.ocortez.com`. The data host was the remaining public surface still carrying the org's name: every documented query URL, every download link on the landing, and every `source_url` in `instances.parquet` read `huggingface.co/datasets/sumpalabs/petrodb/...`.

## Decision

The dataset repo lives at **`oskrgab/petrodb`**. It was **transferred**, not recreated, on 2026-11-12, so its history and both branches (`main`, `stage`) carried over. The public base is now

`https://huggingface.co/datasets/oskrgab/petrodb/resolve/<branch>/<dataset>/...`

Everything else in ADR-0005 stands unchanged: one monorepo mirroring `parquet/`, the two-branch mapping, the `hf upload` deploy, the landing on Cloudflare Pages, and the layout conventions of ADR-0004. This is a namespace swap, not a URL-space change.

The deploy workflow also **pins the `hf` CLI** (`huggingface_hub[cli,hf_xet]==2.4.0`). The first deploy after the move failed because the unpinned CLI had renamed its `repo` command group to `repos`; CLI upgrades are now a deliberate edit.

## Considered alternatives

- **Leave the repo under `sumpalabs`.** Rejected: it contradicts ADR-0007's rule and keeps petrodb's most-used public URLs inside the namespace that rule excludes.
- **Create a fresh `oskrgab/petrodb` and let CI repopulate it.** Rejected: it discards the repo history, and the old URLs would serve stale data until the old repo was deleted and 404 afterwards. A transfer keeps history and makes Hugging Face redirect the old paths.

## Consequences

- `vars.BASE_URL_MAIN` / `vars.BASE_URL_STAGE`, the workflow's `hf` commands, `CANONICAL_HF_BASE` in `scripts/deploy/retarget_data_urls.py`, and all committed data URLs (landing, READMEs, dataset card, analysis-script defaults) name `oskrgab/petrodb`. `CANONICAL_HF_BASE` must keep matching `vars.BASE_URL_MAIN`.
- Old `sumpalabs/petrodb` URLs **redirect** (HTTP 307) to the new repo, for both the API and `resolve` paths, so existing consumers and previously published `source_url` values keep working. The redirect lasts only while nobody creates a new `sumpalabs/petrodb` repo; treat the old path as deprecated, not as an alias.
- `instances.parquet` was rebuilt on both branches, so its `source_url` values now carry the new base. The 3W cache key includes `BASE_URL`, which forced that rebuild.
- The existing `HF_TOKEN` secret kept working: it is a user token with write access, not scoped to the org repo as ADR-0005 describes.
- ADR-0005's text still names `sumpalabs/petrodb`; it is left as the record of the original decision and should be read with this ADR.
