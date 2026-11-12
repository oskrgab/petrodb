<script lang="ts">
  import "../app.css";
  import ThemeToggle from "$lib/components/ThemeToggle.svelte";

  let { children } = $props();
</script>

<a class="skip" href="#main">Skip to content</a>

<!-- Same header anatomy as petroviz: logo tile, lowercase name, mono nav, GitHub, theme. -->
<header class="site">
  <div class="wrap bar">
    <div class="left">
      <a class="brand" href="/">
        <span class="tile" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <ellipse cx="12" cy="6" rx="7" ry="3" />
            <path d="M5 6v6c0 1.66 3.13 3 7 3s7-1.34 7-3V6" />
            <path d="M5 12v6c0 1.66 3.13 3 7 3s7-1.34 7-3v-6" />
          </svg>
        </span>
        <span class="name">petrodb</span>
      </a>
      <nav aria-label="Site">
        <a href="/#datasets">Datasets</a>
        <a href="https://petroviz.ocortez.com/">Explore in petroviz</a>
      </nav>
    </div>
    <div class="right">
      <a
        class="github"
        href="https://github.com/oskrgab/petrodb"
        aria-label="View on GitHub"
        title="View on GitHub"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill-rule="evenodd"
            clip-rule="evenodd"
            d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33s1.71.11 2.5.33c1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2z"
          />
        </svg>
      </a>
      <ThemeToggle />
    </div>
  </div>
</header>

<main id="main">
  {@render children()}
</main>

<footer class="site">
  <div class="wrap foot fine">
    <p>
      See this data drawn in <a href="https://petroviz.ocortez.com/">petroviz</a>. Files on
      <a href="https://huggingface.co/datasets/oskrgab/petrodb">Hugging Face</a>. The data belongs
      to its publishers; each dataset page states its source and licence.
    </p>
    <p>Made with ❤️ by <a href="https://ocortez.com">Oscar Cortez</a></p>
  </div>
</footer>

<style>
  .skip {
    position: absolute;
    left: -999px;
  }

  .skip:focus {
    left: 1rem;
    top: 1rem;
    background: var(--surface);
    padding: 0.5rem 0.75rem;
    z-index: 10;
  }

  header.site {
    position: sticky;
    top: 0;
    z-index: 5;
    background: color-mix(in srgb, var(--paper) 92%, transparent);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--rule);
  }

  .bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    min-height: 60px;
  }

  .left,
  .right {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    min-width: 0;
  }

  .right {
    gap: 1rem;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    text-decoration: none;
    flex-shrink: 0;
  }

  .tile {
    display: grid;
    place-items: center;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--accent) 0%, var(--gas) 100%);
    color: #fff;
  }

  .tile svg {
    width: 1.4rem;
    height: 1.4rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
  }

  .name {
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.03em;
  }

  nav {
    display: flex;
    gap: 0.25rem;
    padding-left: 1rem;
    border-left: 1px solid var(--rule);
    overflow-x: auto;
    scrollbar-width: none;
  }

  nav a {
    font-family: var(--mono);
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--ink-2);
    text-decoration: none;
    white-space: nowrap;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }

  nav a:hover {
    color: var(--ink);
    background: var(--accent-soft);
  }

  .github {
    display: grid;
    color: var(--ink-3);
  }

  .github:hover {
    color: var(--ink);
  }

  .github svg {
    width: 1.25rem;
    height: 1.25rem;
    fill: currentColor;
  }

  main {
    min-height: 70vh;
  }

  footer.site {
    margin-top: 6rem;
    border-top: 1px solid var(--rule);
    padding-block: 1.5rem 2rem;
  }

  .foot {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0.75rem 2rem;
    font-weight: 400;
  }

  .foot p {
    max-width: 60ch;
  }

  .foot a {
    color: var(--ink);
    font-weight: 600;
  }

  @media (max-width: 34rem) {
    .name {
      display: none;
    }

    nav {
      padding-left: 0.5rem;
    }
  }
</style>
