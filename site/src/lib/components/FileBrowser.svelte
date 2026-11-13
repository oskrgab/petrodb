<script lang="ts">
  import { filterFiles, shownCount } from "$lib/files";
  import { live } from "$lib/live.svelte";
  import type { FileLink, FileSearch, TableFile } from "$lib/types";
  import FileList from "./FileList.svelte";

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
    search = {},
  }: { table: string; files: TableFile[]; dataBase: string; searchable?: boolean; search?: FileSearch } =
    $props();

  // Each file is named by its path inside the table, as the Manifest lists it.
  const links: FileLink[] = $derived(
    files.map((f) => ({ name: f.path.replace(`${table}/`, ""), href: `${dataBase}/${f.path}`, bytes: f.bytes })),
  );

  let query = $state("");
  const running = live();
  const shown = $derived(filterFiles(links, query, search.spellings));
</script>

<div class="browser">
  {#if searchable && running.current}
    <div class="search">
      <label class="fine" for={`find-${table}`}>Find a file</label>
      <input
        id={`find-${table}`}
        class="field"
        type="search"
        bind:value={query}
        placeholder={search.placeholder ? `e.g. ${search.placeholder}` : undefined}
        autocomplete="off"
        spellcheck="false"
      />
      <span class="fine num" aria-live="polite">{shownCount(shown.length, links.length, "files")}</span>
    </div>
  {/if}
  <FileList files={shown} />
</div>

<style>
  .browser {
    display: grid;
    gap: 0.5rem;
    margin: 0.75rem 0 1rem 1.25rem;
  }

  .search {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.75rem;
  }

  input {
    flex: 1 1 12rem;
    max-width: 20rem;
  }
</style>
