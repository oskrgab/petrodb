<script lang="ts">
  import { onMount } from "svelte";
  import FileBrowser from "$lib/components/FileBrowser.svelte";
  import Snippet from "$lib/components/Snippet.svelte";
  import Track from "$lib/components/Track.svelte";
  import { approx, bytes, count } from "$lib/format";

  let { data } = $props();
  const { summary, about, units, source, glances, queries, tables, dataBase } = $derived(data);

  const sections = [
    { id: "overview", label: "Overview" },
    { id: "glances", label: "Glances" },
    { id: "query", label: "Query it" },
    { id: "tables", label: "Tables" },
    { id: "files", label: "Files" },
    { id: "licence", label: "Source and licence" },
  ];

  const totalRows = $derived(tables.reduce((sum, t) => sum + t.rows, 0));
  const totalBytes = $derived(tables.reduce((sum, t) => sum + t.bytes, 0));
  const docs = ["schema.md", "schema.json", "schema.sql"];
  // A table with more parts than this opens with its parts listed and a search box.
  const SEARCH_FROM = 24;

  // Mark the section being read in the side list.
  let current = $state("overview");
  onMount(() => {
    const seen = new IntersectionObserver(
      (hits) => {
        for (const hit of hits) if (hit.isIntersecting) current = hit.target.id;
      },
      { rootMargin: "-20% 0px -70% 0px" },
    );
    for (const s of sections) {
      const el = document.getElementById(s.id);
      if (el) seen.observe(el);
    }
    return () => seen.disconnect();
  });
</script>

<svelte:head>
  <title>{summary.name} | PetroDB</title>
  <meta name="description" content={summary.holds} />
  <link rel="canonical" href={`https://petrodb.ocortez.com/${summary.id}/`} />
</svelte:head>

<div class="wrap page">
  <nav class="contents" aria-label="On this page">
    <a class="fine back" href="/#datasets">All datasets</a>
    <ul>
      {#each sections as s}
        <li><a href={`#${s.id}`} aria-current={current === s.id ? "true" : undefined}>{s.label}</a></li>
      {/each}
    </ul>
  </nav>

  <div class="body">
    <section id="overview">
      <h1>{summary.name}</h1>
      <p class="lede">{summary.holds}</p>

      <dl class="facts">
        <div><dt class="fine">One row per</dt><dd>{summary.grain}</dd></div>
        <div><dt class="fine">Covers</dt><dd>{summary.covers}</dd></div>
        <div><dt class="fine">Rows</dt><dd class="num">{approx(totalRows)}</dd></div>
        <div><dt class="fine">Size</dt><dd class="num">{bytes(totalBytes)} in {tables.length} {tables.length === 1 ? "table" : "tables"}</dd></div>
        <div>
          <dt class="fine">Licence</dt>
          <dd><a href="#licence">{summary.licence.name}</a></dd>
        </div>
      </dl>

      <div class="prose">
        {#each about as paragraph}
          <p>{@html paragraph}</p>
        {/each}
      </div>
    </section>

    <section id="glances">
      <h2>Glances</h2>
      <p class="intro">
        A few things the data shows, each with the query that produced it. Copy one and change it.
      </p>
      {#each glances as g (g.id)}
        <article class="glance">
          <h3>{g.title}</h3>
          <div class="pair">
            <figure>
              <Track chart={g.chart} label={g.takeaway} />
              <figcaption>{g.takeaway}</figcaption>
            </figure>
            <Snippet snippets={g.snippets} label={g.title} />
          </div>
        </article>
      {/each}
    </section>

    <section id="query">
      <h2>Query it</h2>
      {#if summary.petroviz}
        <p class="explore">
          <a class="button" href={summary.petroviz.url}>{summary.petroviz.label}</a>
          <span class="fine">Rather look before you query? petroviz charts this dataset in your browser.</span>
        </p>
      {/if}
      <p class="intro">
        Nothing to download. These run against the published files from the DuckDB shell or from
        Python.
      </p>
      {#each queries as q (q.id)}
        <article class="query">
          <h3>{q.title}</h3>
          <p>{q.why}</p>
          <Snippet snippets={q.snippets} label={q.title} />
        </article>
      {/each}

      {#if units.length}
        <h3 class="sub">Units</h3>
        <table class="plain">
          <tbody>
            {#each units as u}
              <tr><th scope="row"><code>{u.column}</code></th><td>{u.unit}</td></tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </section>

    <section id="tables">
      <h2>Tables</h2>
      <p class="intro">Open a table to see its columns. Key columns are marked.</p>
      {#each tables as t (t.name)}
        <details>
          <summary>
            <code class="tname">{t.name}</code>
            <span class="fine num">{count(t.rows)} rows, {t.columns.length} columns</span>
          </summary>
          <div class="tbody">
            <p>{@html t.description}</p>
            {#if t.references.length}
              <p class="fine">Joins: {#each t.references as r, i}{i ? ", " : ""}<code>{r}</code>{/each}</p>
            {/if}
            <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
            <div class="scroll" tabindex="0" role="region" aria-label={`Columns of ${t.name}`}>
              <table class="columns">
                <thead>
                  <tr class="fine"><th scope="col">Column</th><th scope="col">Type</th><th scope="col">What it holds</th></tr>
                </thead>
                <tbody>
                  {#each t.columns as c}
                    <tr>
                      <th scope="row">
                        <code>{c.name}</code>{#if c.key}<span class="keymark fine">key</span>{/if}
                      </th>
                      <td class="fine">{c.type.toLowerCase()}</td>
                      <td>{@html c.description}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        </details>
      {/each}
    </section>

    <section id="files">
      <h2>Files</h2>
      <p class="intro">
        Use these addresses in a query, or download the files. They are served from Hugging Face.
      </p>
      <ul class="files">
        {#each tables as t (t.name)}
          {#if t.kind === "single"}
            <li>
              <a href={`${dataBase}/${t.path}`}><code>{t.path}</code></a>
              <span class="fine num">{bytes(t.bytes)}</span>
            </li>
          {:else}
            <li class="multi">
              <details open={t.files.length > SEARCH_FROM}>
                <summary>
                  <code>{t.name}/</code>
                  <span class="fine num">{t.files.length} files, {bytes(t.bytes)}</span>
                </summary>
                <p class="fine">
                  The list of parts is <a href={`${dataBase}/${t.manifest}`}><code>{t.manifest}</code></a>.
                </p>
                <FileBrowser
                  table={t.name}
                  files={t.files}
                  {dataBase}
                  searchable={t.files.length > SEARCH_FROM}
                />
              </details>
            </li>
          {/if}
        {/each}
      </ul>
      <h3 class="sub">Schema documents</h3>
      <p class="docs">
        {#each docs as doc}
          <a href={doc}><code>{doc}</code></a>
        {/each}
      </p>
    </section>

    <section id="licence">
      <h2>Source and licence</h2>
      <div class="prose">
        <p>{@html source}</p>
        <p>
          Licensed under <a href={summary.licence.url}>{summary.licence.name}</a>.
          {summary.licence.note ?? ""}
        </p>
      </div>
    </section>
  </div>
</div>

<style>
  .page {
    display: grid;
    grid-template-columns: 11rem minmax(0, 1fr);
    gap: clamp(1.5rem, 4vw, 4rem);
    margin-top: clamp(2rem, 5vw, 3.5rem);
  }

  .contents {
    position: sticky;
    top: 5rem;
    align-self: start;
  }

  .contents ul {
    list-style: none;
    margin: 1rem 0 0;
    padding: 0;
    border-left: 1px solid var(--rule);
  }

  .contents li a {
    display: block;
    padding: 0.3rem 0 0.3rem 0.9rem;
    margin-left: -1px;
    border-left: 2px solid transparent;
    text-decoration: none;
    color: var(--ink-2);
    font-size: 0.95rem;
  }

  .contents li a:hover {
    color: var(--ink);
  }

  .contents li a[aria-current] {
    color: var(--ink);
    font-weight: 600;
    border-left-color: var(--accent);
  }

  .body {
    min-width: 0;
  }

  section + section {
    margin-top: clamp(3rem, 7vw, 5rem);
  }

  h1 {
    font-size: clamp(2.25rem, 1.4rem + 3.4vw, 3.5rem);
  }

  .lede {
    margin-top: 1rem;
    font-size: 1.125rem;
    color: var(--ink-2);
    max-width: 58ch;
  }

  .facts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
    margin: 2rem 0;
    border-block: 1px solid var(--ink);
  }

  .facts div {
    padding: 0.8rem 1rem 0.9rem 0;
  }

  .facts dd {
    margin: 0.15rem 0 0;
    font-weight: 600;
    line-height: 1.3;
  }

  .prose {
    display: grid;
    gap: 0.9rem;
  }

  .explore {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem 1rem;
    margin-top: 1.5rem;
  }

  .intro {
    margin-top: 0.6rem;
    color: var(--ink-2);
  }

  .glance {
    margin-top: 2.5rem;
  }

  .pair {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
    gap: clamp(1rem, 2.5vw, 2rem);
    margin-top: 0.9rem;
    align-items: start;
  }

  figure {
    margin: 0;
  }

  figcaption {
    margin-top: 0.6rem;
    color: var(--ink-2);
    font-size: 0.975rem;
  }

  .query {
    display: grid;
    gap: 0.6rem;
    margin-top: 2.25rem;
  }

  .query p {
    color: var(--ink-2);
  }

  .sub {
    margin-top: 2.25rem;
    font-size: 1.1rem;
  }

  table {
    border-collapse: collapse;
    text-align: left;
    font-size: 0.95rem;
  }

  th {
    font-weight: 400;
  }

  .plain {
    margin-top: 0.6rem;
  }

  .plain th,
  .plain td {
    padding: 0.35rem 1.5rem 0.35rem 0;
    border-bottom: 1px solid var(--rule);
    vertical-align: top;
  }

  details {
    border-bottom: 1px solid var(--rule);
  }

  #tables details:first-of-type {
    margin-top: 1.25rem;
    border-top: 1px solid var(--ink);
  }

  summary {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.25rem 1rem;
    padding: 0.8rem 0;
    cursor: pointer;
    list-style: none;
  }

  summary::-webkit-details-marker {
    display: none;
  }

  summary::before {
    content: "+";
    font-family: var(--mono);
    width: 1.25rem;
    color: var(--ink-3);
  }

  details[open] > summary::before {
    content: "−";
  }

  summary .fine {
    margin-left: auto;
  }

  .tname {
    font-size: 1rem;
    font-weight: 600;
    background: none;
    padding: 0;
  }

  .tbody {
    display: grid;
    gap: 0.75rem;
    padding: 0 0 1.5rem 1.25rem;
  }

  .scroll {
    overflow-x: auto;
  }

  .columns {
    width: 100%;
    min-width: 34rem;
  }

  .columns th,
  .columns td {
    padding: 0.4rem 1rem 0.4rem 0;
    border-top: 1px solid var(--grid);
    vertical-align: top;
  }

  .columns thead th {
    border-top: 0;
    font-weight: 500;
  }

  .columns tbody th {
    white-space: nowrap;
  }

  .keymark {
    margin-left: 0.5rem;
    padding: 0 0.35rem;
    border: 1px solid var(--ink-3);
    border-radius: 3px;
    font-size: 0.75rem;
  }

  .files {
    list-style: none;
    margin: 1.25rem 0 0;
    padding: 0;
    border-top: 1px solid var(--ink);
  }

  .files > li:not(.multi) {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--rule);
  }

  .multi summary {
    padding: 0.6rem 0;
  }

  .multi details > .fine {
    padding-left: 1.25rem;
  }

  .docs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    margin-top: 0.6rem;
  }

  @media (max-width: 56rem) {
    .page {
      grid-template-columns: minmax(0, 1fr);
    }

    .contents {
      position: static;
    }

    .contents ul {
      display: flex;
      gap: 0.25rem 1.25rem;
      overflow-x: auto;
      border-left: 0;
      border-bottom: 1px solid var(--rule);
      margin-top: 0.6rem;
    }

    .contents li a {
      padding: 0.4rem 0;
      margin: 0 0 -1px;
      border-left: 0;
      border-bottom: 2px solid transparent;
      white-space: nowrap;
    }

    .contents li a[aria-current] {
      border-bottom-color: var(--accent);
    }

    .pair {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
