<script lang="ts">
  import Plot from "$lib/components/Plot.svelte";
  import Snippet from "$lib/components/Snippet.svelte";
  import Track from "$lib/components/Track.svelte";

  let { data } = $props();
  const { datasets, opener } = $derived(data);
</script>

<svelte:head>
  <title>PetroDB: open petroleum datasets in Parquet</title>
  <meta
    name="description"
    content="Four public oil and gas datasets, cleaned into Parquet tables you can query straight from a URL with DuckDB, Python or Polars."
  />
  <link rel="canonical" href="https://petrodb.ocortez.com/" />
</svelte:head>

<section class="wrap opener">
  <h1>Query open petroleum data straight from a URL</h1>
  <p class="lede">
    PetroDB republishes four public oil and gas datasets as clean Parquet tables. There is nothing
    to download and no account to create: point DuckDB at a file and ask your question.
  </p>

  <div class="pair">
    <div class="ask">
      <Snippet snippets={opener.snippets} label={opener.title} />
      <p class="fine">
        Runs as it is in the <a href="https://duckdb.org/docs/installation/">DuckDB shell</a>, or
        after <code>pip install duckdb</code> in Python.
      </p>
    </div>
    <figure>
      <Track chart={opener.chart} label={opener.takeaway} />
      <figcaption>
        <strong>What comes back.</strong>
        {opener.takeaway} This is the Volve field in the North Sea, one of the four datasets below.
      </figcaption>
    </figure>
  </div>
</section>

<section class="wrap">
  <div class="look">
    <div>
      <h2>Rather look than write a query?</h2>
      <p>
        petroviz is a companion app that charts PetroDB data in your browser, with nothing to
        install. Today it covers Volve production and FORCE 2020 well logs.
      </p>
    </div>
    <a class="button" href="https://petroviz.ocortez.com/">Open petroviz</a>
  </div>
</section>

<section class="wrap" id="datasets">
  <h2>Datasets</h2>
  <div class="catalogue">
    <div class="row head fine" aria-hidden="true">
      <span>Dataset</span>
      <span>One row per</span>
      <span>Covers</span>
      <span>Size</span>
      <span>A glance</span>
    </div>
    {#each datasets as d (d.id)}
      <article class="row">
        <div class="what">
          <h3>
            {#if d.ready}
              <a href={`/${d.id}/`}>{d.name}</a>
            {:else}
              {d.name}
            {/if}
          </h3>
          <p>{d.holds}</p>
          {#if d.petroviz}
            <p class="fine"><a href={d.petroviz.url}>{d.petroviz.label}</a> in petroviz</p>
          {/if}
        </div>
        <p class="cell"><span class="fine key">One row per</span>{d.grain}</p>
        <p class="cell"><span class="fine key">Covers</span>{d.covers}</p>
        <p class="cell num"><span class="fine key">Size</span>{d.size}</p>
        <div class="spark">
          {#if d.spark}
            <Plot chart={d.spark} grid={false} label={`Sample of ${d.name} data`} />
          {/if}
        </div>
      </article>
    {/each}
  </div>
</section>

<section class="wrap basics">
  <h2>What you are querying</h2>
  <dl>
    <div>
      <dt>Plain Parquet files</dt>
      <dd>
        Every table is a Parquet file at a fixed address on Hugging Face. Anything that reads
        Parquet can use it: DuckDB, Polars, pandas, R, Spark.
      </dd>
    </div>
    <div>
      <dt>Only the bytes you need</dt>
      <dd>
        Query engines read Parquet over the network a piece at a time. Ask for one well out of
        tens of thousands and a few hundred kilobytes travel, not the whole table.
      </dd>
    </div>
    <div>
      <dt>Large tables come in parts</dt>
      <dd>
        A table too big for one file is split into several, with a small <code>_files.json</code>
        beside them listing every part. Each dataset page shows how to read it.
      </dd>
    </div>
  </dl>
</section>

<style>
  section {
    margin-top: clamp(3.5rem, 8vw, 6rem);
  }

  .opener {
    margin-top: clamp(2.5rem, 6vw, 4.5rem);
  }

  h1 {
    max-width: 20ch;
  }

  .lede {
    margin-top: 1.25rem;
    font-size: 1.125rem;
    color: var(--ink-2);
    max-width: 60ch;
  }

  .pair {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: clamp(1.25rem, 3vw, 2.5rem);
    margin-top: clamp(2rem, 5vw, 3.5rem);
    align-items: start;
  }

  .ask {
    display: grid;
    gap: 0.75rem;
  }

  figure {
    margin: 0;
  }

  figcaption {
    margin-top: 0.75rem;
    color: var(--ink-2);
    font-size: 0.975rem;
    max-width: var(--measure);
  }

  figcaption strong {
    color: var(--ink);
  }

  .look {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1.25rem 2.5rem;
    padding: 1.5rem 1.75rem;
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
  }

  .look h2 {
    font-size: 1.4rem;
  }

  .look p {
    margin-top: 0.4rem;
    color: var(--ink-2);
  }

  .catalogue {
    margin-top: 1.5rem;
    border-top: 1px solid var(--ink);
  }

  .row {
    display: grid;
    grid-template-columns: minmax(0, 2.6fr) minmax(0, 1.1fr) minmax(0, 1.2fr) 5.5rem minmax(0, 1.3fr);
    gap: 1.5rem;
    align-items: start;
    padding-block: 1.4rem;
    border-bottom: 1px solid var(--rule);
  }

  .row.head {
    padding-block: 0.5rem;
    border-bottom-color: var(--ink);
  }

  .what {
    display: grid;
    gap: 0.4rem;
  }

  .what p {
    color: var(--ink-2);
    font-size: 0.975rem;
  }

  .what .fine {
    color: var(--ink-2);
  }

  .cell {
    font-size: 0.975rem;
  }

  .key {
    display: none;
  }

  .spark {
    height: 3.5rem;
    align-self: center;
  }

  .basics dl {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 2rem;
    margin: 1.5rem 0 0;
  }

  dt {
    font-weight: 600;
    padding-top: 0.75rem;
    border-top: 1px solid var(--ink);
  }

  dd {
    margin: 0.4rem 0 0;
    color: var(--ink-2);
    font-size: 0.975rem;
  }

  @media (max-width: 60rem) {
    .pair {
      grid-template-columns: minmax(0, 1fr);
    }

    .row.head {
      display: none;
    }

    .row {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 0.9rem 1.5rem;
    }

    .what,
    .spark {
      grid-column: 1 / -1;
    }

    .key {
      display: block;
    }

    .basics dl {
      grid-template-columns: minmax(0, 1fr);
      gap: 1.25rem;
    }
  }
</style>
