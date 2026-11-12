# Build the Landing as a prerendered SvelteKit site

**Status:** accepted — supplements [ADR-0005](0005-host-parquet-on-huggingface.md) and [ADR-0007](0007-landing-hosts-independently-of-sumpalabs-apex.md); hosting is unchanged

## Context

The Landing was a single hand-written `parquet/index.html`: four Datasets as tabs on one page, about 2,850 lines. Two of the tabs were Python f-strings spliced between sentinel comments by each pipeline's `website_integrator`, with tests asserting on the exact markup; the other two were written by hand, including 108 hard-coded FORCE 2020 download links. It had no build step, sat inside the data tree, and offered one Python snippet per Dataset as its only guidance.

We want a Landing that is easier to navigate (a catalogue page plus one page per Dataset), teaches several ways to query the data, and shows Glances. That is more pages and more shared structure than sentinel patching can carry.

## Decision

The Landing becomes a SvelteKit project in `site/`, built with `adapter-static` and prerendered in full. Its build output, together with the per-Dataset schema documents at their existing paths, is the Cloudflare Pages deploy tree. `parquet/index.html` is removed.

- **Pipelines emit data, never markup.** Each Dataset has one committed metadata file that the site reads at build time, next to its `schema.json`. File lists come from the Manifests. The `website_integrator` modules keep only their root-README patching.
- **Glances are computed ahead of the site build.** A Python command queries the data with DuckDB and writes small JSON files that are committed. The site build needs Node only and never reads parquet. Glances are regenerated when a Dataset is re-exported, not on every deploy.
- **Charts are prerendered SVG.** No page needs JavaScript or a network call to Hugging Face to show its content.
- **Existing URLs keep working.** `/<dataset>/schema.md`, `schema.json`, `schema.sql` and `README.md` stay where they are; petroviz links to them.

## Considered options

- **Jinja templates rendered by Python.** Keeps the repo single-language and was the first recommendation. Rejected in favour of a frontend toolchain with room to grow into in-browser querying.
- **Astro with Svelte components.** Ships less JavaScript for pure content pages. Rejected because petroviz already runs SvelteKit 2, Svelte 5, `adapter-static` and DuckDB-WASM: one stack across both sites means shared components and one set of habits, and the performance difference is small at this size.
- **Live Glances with DuckDB-WASM.** Rejected for now: a large download and a failure mode on the first page a visitor sees. Each Glance carries its query so a "run it" control can be added later without reshaping the data.

## Consequences

- The deploy workflow and `deploy.sh` gain a Node build step; the repo gains a second toolchain.
- Tests that asserted on generated HTML are replaced by tests on the Dataset metadata.
- A stale Glance is possible if a Dataset is re-exported without regenerating it. The export pipelines must run the Glance command, or a check must compare the two.
