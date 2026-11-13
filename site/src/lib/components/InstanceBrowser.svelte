<script lang="ts">
  import { shownCount } from "$lib/files";
  import { count } from "$lib/format";
  import { filterInstances } from "$lib/instances";
  import { live } from "$lib/live.svelte";
  import type { FileSearch, InstanceGroup } from "$lib/types";
  import FileList from "./FileList.svelte";

  /*
   * Every Observation file, grouped by Event class. The whole list is in the
   * prerendered page; the two filters appear only once JavaScript is running,
   * and only narrow what is already there.
   */
  let {
    groups,
    dataBase,
    search = {},
  }: { groups: InstanceGroup[]; dataBase: string; search?: FileSearch } = $props();

  let eventClass = $state("all");
  let query = $state("");
  const running = live();

  const total = $derived(groups.reduce((sum, g) => sum + g.files.length, 0));
  const shown = $derived(filterInstances(groups, eventClass, query, search.spellings));
  const matches = $derived(shown.reduce((sum, g) => sum + g.files.length, 0));
</script>

<div class="browser">
  {#if running.current}
    <div class="filters">
      <label>
        <span class="fine">Event class</span>
        <select class="field" bind:value={eventClass}>
          <option value="all">All {groups.length} Event classes</option>
          {#each groups as g}
            <option value={String(g.eventClass)}>{g.eventClass} · {g.description} ({g.files.length})</option>
          {/each}
        </select>
      </label>
      <label>
        <span class="fine"><code>instance_id</code> contains</span>
        <input
          class="field"
          type="search"
          bind:value={query}
          placeholder={search.placeholder ? `e.g. ${search.placeholder}` : undefined}
          autocomplete="off"
          spellcheck="false"
        />
      </label>
    </div>
    <p class="fine count" aria-live="polite">{shownCount(matches, total, "Instances")}</p>
  {/if}

  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div class="list" tabindex="0" role="region" aria-label="Observation files by Event class">
    {#each shown as g (g.eventClass)}
      <section>
        <h4>
          <span class="num">{g.eventClass}</span>
          {g.description}
          <span class="fine num">{count(g.files.length)} files</span>
        </h4>
        <FileList files={g.files.map((f) => ({ name: f.name, href: `${dataBase}/${f.path}`, bytes: f.bytes }))} />
      </section>
    {:else}
      <p class="fine">No Instance matches.</p>
    {/each}
  </div>
</div>

<style>
  .browser {
    padding: 0.5rem 0 1rem 1.25rem;
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1.5rem;
  }

  label {
    display: grid;
    gap: 0.25rem;
  }

  .count {
    margin-top: 0.6rem;
  }

  .list {
    max-height: 32rem;
    overflow-y: auto;
    margin-top: 0.5rem;
    border-top: 1px solid var(--rule);
  }

  h4 {
    display: flex;
    gap: 0.6rem;
    align-items: baseline;
    margin: 1rem 0 0.25rem;
    font-size: 1rem;
  }

  h4 .fine {
    margin-left: auto;
  }
</style>
