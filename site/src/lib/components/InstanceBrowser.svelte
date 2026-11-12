<script lang="ts">
  import { onMount } from "svelte";
  import { bytes, count } from "$lib/format";
  import { filterInstances } from "$lib/instances";
  import type { InstanceGroup } from "$lib/types";

  /*
   * Every Observation file, grouped by Event class. The whole list is in the
   * prerendered page; the two filters only narrow it once the page has loaded.
   */
  /** `base` is the Observations table's URL, where the `event_class=N/` folders sit. */
  let { groups, base }: { groups: InstanceGroup[]; base: string } = $props();

  let eventClass = $state("all");
  let search = $state("");
  // Without JavaScript the filters could not work, so they appear only once it runs.
  let live = $state(false);
  onMount(() => (live = true));

  const total = $derived(groups.reduce((sum, g) => sum + g.files.length, 0));
  const shown = $derived(filterInstances(groups, eventClass, search));
  const matches = $derived(shown.reduce((sum, g) => sum + g.files.length, 0));
</script>

<div class="browser">
  {#if live}
    <div class="filters">
      <label>
        <span class="fine">Event class</span>
        <select bind:value={eventClass}>
          <option value="all">All {groups.length} Event classes</option>
          {#each groups as g}
            <option value={String(g.eventClass)}>{g.eventClass} · {g.description} ({g.files.length})</option>
          {/each}
        </select>
      </label>
      <label>
        <span class="fine"><code>instance_id</code> contains</span>
        <input type="search" bind:value={search} placeholder="WELL-00032" autocomplete="off" spellcheck="false" />
      </label>
    </div>
    <p class="fine count" aria-live="polite">
      {matches === total ? `${count(total)} Instances` : `${count(matches)} of ${count(total)} Instances`}
    </p>
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
        <ul>
          {#each g.files as f (f.instanceId)}
            <li>
              <a href={`${base}/event_class=${g.eventClass}/${f.instanceId}.parquet`}><code>{f.instanceId}</code></a>
              <span class="fine num">{bytes(f.bytes)}</span>
            </li>
          {/each}
        </ul>
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

  select,
  input {
    font: inherit;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 0.35rem 0.5rem;
    max-width: 100%;
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

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    columns: 2 16rem;
    column-gap: 2rem;
  }

  li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid var(--grid);
    break-inside: avoid;
  }
</style>
