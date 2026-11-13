<script lang="ts">
  import Snippet from "$lib/components/Snippet.svelte";

  let { data } = $props();
  const { intro, steps } = $derived(data);
</script>

<svelte:head>
  <title>Query the data | PetroDB</title>
  <meta
    name="description"
    content="How to read any PetroDB Dataset with DuckDB or Polars: one file, a Multi-parquet table through its Manifest, filtering, pinning a version and downloading."
  />
  <link rel="canonical" href="https://petrodb.ocortez.com/query/" />
</svelte:head>

<div class="wrap page">
  <h1>Query the data</h1>
  <div class="prose lede">
    {#each intro as paragraph}
      <p>{@html paragraph}</p>
    {/each}
  </div>

  <ol class="steps">
    {#each steps as step, i (step.id)}
      <li id={step.id}>
        <h2><span class="n num" aria-hidden="true">{i + 1}</span>{step.title}</h2>
        <div class="prose">
          {#each step.body as paragraph}
            <p>{@html paragraph}</p>
          {/each}
          {#each step.missing as reason}
            <p class="fine">{reason}</p>
          {/each}
        </div>
        <Snippet snippets={step.snippets} label={step.title} />
      </li>
    {/each}
  </ol>
</div>

<style>
  .page {
    max-width: 52rem;
    margin-top: clamp(2rem, 5vw, 3.5rem);
  }

  h1 {
    font-size: clamp(2.25rem, 1.4rem + 3.4vw, 3.5rem);
  }

  .prose {
    display: grid;
    gap: 0.9rem;
  }

  .lede {
    margin-top: 1rem;
    color: var(--ink-2);
  }

  .lede p:first-child {
    font-size: 1.125rem;
  }

  .steps {
    list-style: none;
    margin: clamp(2.5rem, 6vw, 4rem) 0 0;
    padding: 0;
    display: grid;
    gap: clamp(3rem, 7vw, 4.5rem);
  }

  .steps li {
    display: grid;
    gap: 1rem;
    min-width: 0;
  }

  h2 {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    padding-top: 0.8rem;
    border-top: 1px solid var(--ink);
  }

  .n {
    font-family: var(--mono);
    font-size: 0.9rem;
    color: var(--accent);
  }
</style>
