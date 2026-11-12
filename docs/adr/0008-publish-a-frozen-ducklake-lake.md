# Publish a frozen DuckLake as an optional single entry point (the Lake)

**Status:** proposed — pending the spike described below; supplements [ADR-0004](0004-multi-parquet-table-convention.md)

DuckDB consumers currently discover each multi-parquet table by fetching its `_files.json` and building a URL list. We will publish a **Lake**: one read-only, frozen DuckLake (`petrodb.ducklake`) that registers the already-published parquet files in place via `ducklake_add_data_files` — no bytes copied or rewritten — so a consumer can `ATTACH` one URL and query every Dataset by name, with per-file statistics letting DuckDB skip files without fetching their footers. The Lake is a **convenience entry point, not the contract**: plain parquet at stable URLs plus `_files.json` remain authoritative (ADR-0004 unchanged), so dropping or breaking the Lake breaks no documented access path. ADR-0004 rejected table formats with built-in manifests as too heavy for a static, read-only dataset; a frozen DuckLake is accepted where they were not because it adds no runtime, no transaction log and no rewrite of the data, only one catalog file alongside it.

## Decisions

- **One Lake for all Datasets**, one schema per Dataset (`argentina.wells`, `petrobras_3w.instances`, …). "Attach one URL" is the value; per-Dataset Lakes would reintroduce discovery.
- **Hosted on Hugging Face beside the data**, at `/resolve/<branch>/petrodb.ducklake`, built in CI after the 3W build and URL retarget, uploaded by the same `hf upload`. The Lake stores absolute data URLs, so it must be per-branch like the bytes it references; the off-branch-host CI guard extends to the `.ducklake` file.
- **Rebuilt from empty on every publish** — exactly one snapshot per published Lake. Re-registering a file duplicates its rows, and accumulated snapshots would need old files to stay reachable, which `hf upload --delete` does not guarantee. Pinning a version stays as today: swap `main` for an HF commit SHA, which pins Lake and data together.
- **Builder DuckDB version pinned to what the WASM consumers can read.** The Lake's format follows the `ducklake` extension version it was built with; advancing the pin is a deliberate, coordinated step with petroviz and formuladb.

## Acceptance (the spike)

Run against the `stage` Lake over all four Datasets. All must pass — DuckDB-WASM support is a hard gate because petroviz and formuladb both consume petrodb from the browser / Office shared runtime:

1. `ATTACH` works from the DuckDB CLI and Python; every published table is present with row counts matching manifest-based reads.
2. Hive partition columns (`anio`, `event_class`) are queryable (a view that restores them passes, noted).
3. A single-well Argentina query and a single-class 3W query issue fewer HTTP requests than the manifest path.
4. In each consumer's real runtime and DuckDB-WASM bundle (petroviz in the browser, brought up to formuladb's DuckDB-WASM version; formuladb in the Office shared runtime, EH bundle): load `ducklake`, `ATTACH` the Lake, run the single-well query with the Hive column present. Raw capability only — how formuladb exposes a Lake as a source is decided in formuladb.

Record the Lake's build time and size.

## Considered options

- **Lake as primary entry point or manifest replacement.** Rejected: it would make a young format the front door and tie it to WASM support; promotion from optional is cheap, demotion breaks users.
- **Fallback arm — a plain `petrodb.duckdb` of `CREATE VIEW`s over the published URLs.** Tested alongside the Lake because DuckDB-WASM can attach a remote DuckDB file without an extra extension. Weaker file skipping and it duplicates the manifests' file lists. Adopted only if the Lake fails the WASM gate and the fallback passes, which would require redefining **Lake** in `CONTEXT.md`. Dropped if the Lake passes.
- **If both fail the WASM gate:** this ADR becomes *rejected, pending upstream DuckLake support in DuckDB-WASM*, revisited when that ships.
