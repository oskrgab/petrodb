<script lang="ts">
  import { bytes } from "$lib/format";
  import type { FileLink } from "$lib/types";

  /* Links to a table's files, each with its size, in up to two columns. */
  let { files }: { files: FileLink[] } = $props();
</script>

<ul>
  {#each files as f (f.href)}
    <li>
      <a href={f.href}><code>{f.name}</code></a>
      <span class="fine num">{bytes(f.bytes)}</span>
    </li>
  {/each}
</ul>

<style>
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
