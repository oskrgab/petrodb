# Host the petrodb landing independently of the SumpaLabs apex

**Status:** accepted — supersedes [ADR-0006](0006-landing-at-sumpalabs-subpath.md)

## Context

ADR-0006 moved the human-facing landing off `petrodb.ocortez.com` and onto the subpath `https://sumpalabs.com/petrodb/`, served same-origin by a *sumpalabs umbrella router* on the apex zone. The motive was SEO: consolidate link equity into the apex rather than spread it across product subdomains.

That plan was only partially enacted, and the half that shipped is the half that broke the site. The Pages deploy was changed to stage its output under a `/petrodb/` directory (commit `5bd0271`, issue #38), matching the origin path the router would have proxied. The other two steps never happened: the Pages project's custom domain was never detached, and the router was never built. The landing has therefore been unreachable at every advertised URL since 2026-06-16 — `petrodb.ocortez.com/` returns 404 (content sits one directory deep), `petrodb.ocortez.com/petrodb/` returns 200 but is documented nowhere, and `sumpalabs.com/petrodb/` returns 404.

The router is not late; it is **cancelled**. [`sumpalabs-landing` ADR-0004 — *Remove petrodb, the umbrella router, and all oil-and-gas positioning from the apex site*](https://github.com/sumpalabs/sumpalabs-landing/blob/main/docs/adr/0004-remove-petrodb-and-umbrella-router.md) deleted `functions/` and `lib/` in full and added a build-output guard test asserting a forbidden-term list — including the literal string `petrodb` — against every built apex page. That ADR also records that the router **never served live traffic**: it shipped with a placeholder origin, so `/petrodb/` resolved to nothing real. There is consequently no indexed content, no inbound link equity, and no live URL to unwind.

Critically, ADR-0004's severance was a **business decision** about what SumpaLabs' public presence is — removing oil-and-gas and energy-sector positioning, and petrodb with it — not an SEO or routing preference. That is what makes the host choice a matter of record rather than of convenience: the constraint outlives the router, the subpath, and this particular URL.

## Decision

**petrodb's public hosting is independent of the SumpaLabs apex.** The apex deliberately carries no petrodb tie (`sumpalabs-landing` ADR-0004), so petrodb takes **no dependency on apex-zone infrastructure** — no router, no shared Worker or Pages Function, no route on the `sumpalabs.com` zone, and no host inside the SumpaLabs namespace.

As a consequence of that rule, the landing returns to **`https://petrodb.ocortez.com/`**, served directly by the petrodb Pages project's own custom domain, which was never detached and serves today. The slim Wrangler deploy (landing `index.html` + svg + per-dataset schema docs) stages its content at the **tree root** (`_site/`) rather than under `_site/petrodb/`, so the deployed `index.html` sits at the root of the Pages deployment and the custom domain serves it with no subpath and no redirect. `<link rel="canonical">` and `og:url` point at `https://petrodb.ocortez.com/`. The landing's internal links are all relative and the file contains no absolute `/…` paths, so dropping the `/petrodb/` depth needs no link rewriting.

The data path is untouched: the parquet bytes stay on Hugging Face at the per-branch `resolve` bases (ADR-0005), and the local dev host `dev-petrodb.ocortez.com` (Caddy, ADR-0003) is a different host and is unaffected.

## Considered alternatives

- **`petrodb.sumpalabs.com` (a subdomain of the apex).** Trivial — one custom domain on the existing Pages project, no router, and it sidesteps the mechanical reason ADR-0006 failed. Rejected on the rule above: ADR-0004 severed the *SumpaLabs namespace* from petrodb as a business decision about public positioning, so putting petrodb back into that namespace violates its intent even though ADR-0004's guard test only scans built apex **pages** and would not fail on a DNS record. Passing a guard test is not the same as honouring the decision the guard test protects.
- **Rebuild the umbrella router in petrodb's own repo and keep `sumpalabs.com/petrodb/`.** Rejected for the same reason, and more sharply: it would re-attach the exact surface ADR-0004 deleted, on a zone this project does not own, to publish the exact term its guard test forbids.
- **Wait for the router to return and stay at `/petrodb/` in the meantime.** Rejected: ADR-0004 defers the router for a possible *future* apex-subpath offering, and petrodb is explicitly not that offering. Waiting keeps the landing 404ing at its documented URL indefinitely, for a dependency that will never arrive.
- **Ship a `_redirects` file mapping `/petrodb/*` → `/*`.** Rejected as unnecessary rather than wrong. `sumpalabs.com/petrodb/` never resolved, so nothing is indexed there; `petrodb.ocortez.com/petrodb/` served for three months undocumented, unmonitored and unlinked. There is no traffic or link equity to preserve, and ADR-0006's promised 301 off `petrodb.ocortez.com` was never executed either.

## Consequences

- The public landing URL in the docs, `CONTEXT.md`, and the HF dataset card returns to `https://petrodb.ocortez.com/`. [ADR-0005](0005-host-parquet-on-huggingface.md) already names this host for the landing (lines 16 and 35); this change makes those statements true again rather than requiring an edit.
- petrodb's deploy regains its independence: no cross-repo dependency, no cutover gated on apex-zone work, and the Pages project is publicly reachable standalone again.
- No Cloudflare console, DNS, or domain-attachment work is required. The custom domain was never detached; the 404 was purely a directory-depth artefact of the half-enacted ADR-0006 and is fixed by the staging-path change alone.
- The SEO consolidation ADR-0006 sought is forfeited by design. That is the accepted cost of ADR-0004's severance, not a regression to be fixed later.
- Any future proposal to host petrodb under `sumpalabs.com` — apex subpath or subdomain — must first reopen `sumpalabs-landing` ADR-0004, not merely this one.
