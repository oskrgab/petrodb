<script lang="ts">
  import { preferred } from "$lib/lang.svelte";
  import type { Snippet } from "$lib/types";

  let { snippets, label }: { snippets: Snippet[]; label: string } = $props();

  // Fall back to the first language when this query has no version in the preferred one.
  const active = $derived(snippets.find((s) => s.lang === preferred.lang) ?? snippets[0]);

  let copied = $state(false);

  async function copy() {
    await navigator.clipboard.writeText(active.code);
    copied = true;
    setTimeout(() => (copied = false), 1600);
  }
</script>

<div class="snippet">
  <div class="bar">
    <div class="langs" role="group" aria-label={`Language for: ${label}`}>
      {#each snippets as s (s.lang)}
        <button
          type="button"
          class="fine"
          aria-pressed={s.lang === active.lang}
          onclick={() => (preferred.lang = s.lang)}
        >
          {s.label}
        </button>
      {/each}
    </div>
    <button type="button" class="fine copy" onclick={copy}>{copied ? "Copied" : "Copy"}</button>
  </div>
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div class="code" tabindex="0" role="region" aria-label={`${active.label}: ${label}`}>
    {@html active.html}
  </div>
</div>

<style>
  .snippet {
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    min-width: 0;
  }

  .bar {
    display: flex;
    justify-content: space-between;
    align-items: stretch;
    border-bottom: 1px solid var(--rule);
  }

  .langs {
    display: flex;
  }

  button {
    font-family: var(--mono);
    font-size: 0.75rem;
    background: none;
    border: 0;
    padding: 0.55rem 0.9rem;
    cursor: pointer;
    color: var(--ink-3);
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
  }

  button:hover {
    color: var(--ink);
  }

  button[aria-pressed="true"] {
    color: var(--ink);
    border-bottom-color: var(--accent);
  }

  .code {
    overflow-x: auto;
    padding: 1rem 1.1rem;
  }
</style>
