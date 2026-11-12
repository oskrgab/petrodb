<script lang="ts">
  import { onMount } from "svelte";
  import { bytes } from "$lib/format";
  import type { TableFile } from "$lib/types";

  /*
   * The member files of a Multi-parquet table, as listed by its Manifest.
   * Every file is in the prerendered HTML; the search box appears only once
   * JavaScript is running, and only narrows what is already there.
   */
  let {
    table,
    files,
    dataBase,
    searchable = false,
  }: { table: string; files: TableFile[]; dataBase: string; searchable?: boolean } = $props();

  const nameOf = (f: TableFile) => f.path.replace(`${table}/`, "");

  // Well names are typed as "15/9-13" or "16/11-1 ST3"; files spell them
  // "15-9-13" and "16-11-1_ST3". Compare in one spelling, ignoring case.
  const fold = (s: string) => s.toLowerCase().replaceAll("/", "-").replace(/\s+/g, "_");

  let query = $state("");
  let live = $state(false);
  onMount(() => (live = true));

  const shown = $derived(files.filter((f) => fold(nameOf(f)).includes(fold(query.trim()))));
  const visible = $derived(new Set(shown));
</script>

{#if searchable && live}
  <div class="search">
    <label class="fine" for={`find-${table}`}>Find a file</label>
    <input
      id={`find-${table}`}
      type="search"
      bind:value={query}
      placeholder="e.g. 15/9-13"
      autocomplete="off"
      spellcheck="false"
    />
    <span class="fine num" aria-live="polite">
      {shown.length === files.length ? `${files.length} files` : `${shown.length} of ${files.length} files`}
    </span>
  </div>
{/if}
<ul class="parts">
  {#each files as f (f.path)}
    <li hidden={!visible.has(f)}>
      <a href={`${dataBase}/${f.path}`}><code>{nameOf(f)}</code></a>
      <span class="fine num">{bytes(f.bytes)}</span>
    </li>
  {/each}
</ul>

<style>
  .search {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.75rem;
    margin: 0.75rem 0 0 1.25rem;
  }

  input {
    flex: 1 1 12rem;
    max-width: 20rem;
    padding: 0.45rem 0.6rem;
    font: inherit;
    font-family: var(--mono);
    font-size: 0.9rem;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
  }

  input:focus-visible {
    border-color: var(--accent);
  }

  .parts {
    list-style: none;
    margin: 0.5rem 0 1rem 1.25rem;
    padding: 0;
    columns: 2 14rem;
    column-gap: 2rem;
  }

  .parts li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid var(--grid);
    break-inside: avoid;
  }

  .parts li[hidden] {
    display: none;
  }
</style>
