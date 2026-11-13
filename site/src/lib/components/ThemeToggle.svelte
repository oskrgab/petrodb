<script lang="ts">
  import { onMount } from "svelte";

  // The inline script in app.html has already set data-theme; read it back.
  let dark = $state(false);
  onMount(() => {
    dark = document.documentElement.getAttribute("data-theme") === "dark";
  });

  function toggle() {
    dark = !dark;
    const theme = dark ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("theme", theme);
    } catch {
      // Private mode: the choice lasts for this page only.
    }
  }
</script>

<button
  type="button"
  class="toggle"
  role="switch"
  aria-checked={dark}
  aria-label="Dark theme"
  onclick={toggle}
>
  <span class="knob" aria-hidden="true">
    {#if dark}
      <svg viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
    {:else}
      <svg viewBox="0 0 24 24"
        ><circle cx="12" cy="12" r="4.5" /><path
          d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        /></svg
      >
    {/if}
  </span>
</button>

<style>
  .toggle {
    width: 3.25rem;
    height: 1.75rem;
    padding: 2px;
    border: 1px solid var(--rule);
    border-radius: 999px;
    background: var(--grid);
    cursor: pointer;
    display: flex;
  }

  .knob {
    width: 1.375rem;
    height: 1.375rem;
    border-radius: 50%;
    background: var(--surface);
    color: var(--accent);
    display: grid;
    place-items: center;
    transition: transform 150ms ease;
  }

  .toggle[aria-checked="true"] .knob {
    transform: translateX(1.5rem);
  }

  svg {
    width: 0.85rem;
    height: 0.85rem;
    fill: currentColor;
  }

  @media (prefers-reduced-motion: reduce) {
    .knob {
      transition: none;
    }
  }
</style>
