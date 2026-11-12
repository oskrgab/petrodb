<script lang="ts">
  import { scaleOf, toneVar, xTicks } from "$lib/chart";
  import type { Chart } from "$lib/types";
  import Plot from "./Plot.svelte";

  /*
   * A chart framed like a well-log track: a header strip that names each
   * curve and gives the ends of its scale, above a gridded plot.
   */
  let { chart, label }: { chart: Chart; label: string } = $props();

  const ticks = $derived(xTicks(chart));
  const categories = $derived(chart.x.values.map(String));
  const num = (n: number) => n.toLocaleString("en-US");
</script>

{#if chart.kind === "bars"}
  <div class="bars" role="img" aria-label={label}>
    <div class="cats" style={`grid-template-rows: auto repeat(${categories.length}, 1fr)`}>
      <div class="head-spacer"></div>
      {#each categories as c}
        <div class="cat fine">{c}</div>
      {/each}
    </div>
    {#each chart.series as s}
      {@const scale = scaleOf(chart, s)}
      <div class="track">
        <div class="curve label" style={`--tone: ${toneVar(s.tone)}`}>
          <span class="num">{num(scale.min)}</span>
          <span class="name">{s.name}{s.unit ? `, ${s.unit}` : ""}</span>
          <span class="num">{num(scale.max)}</span>
        </div>
        <div class="rows" style={`grid-template-rows: repeat(${categories.length}, 1fr)`}>
          {#each s.values as v, i}
            <div class="row">
              <span class="rowcat fine">{categories[i]}</span>
              <div class="lane">
                <div
                  class="bar"
                  style={`width: ${((v ?? 0) / scale.max) * 100}%; background: ${toneVar(s.tone)}`}
                ></div>
              </div>
              <span class="value label num">{num(v ?? 0)}</span>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </div>
{:else}
  <div class="track">
    {#if chart.kind === "stacked"}
      <!-- Stacked bands share one scale: state it once, then name each band. -->
      <div class="curve label scale">
        <span class="num">{num(chart.min ?? 0)}</span>
        <span class="name">{chart.unit}</span>
        <span class="num">{num(chart.max ?? 1)}</span>
      </div>
      <div class="bands label">
        {#each chart.series as s}
          <span class="band" style={`--tone: ${toneVar(s.tone)}`}>{s.name}</span>
        {/each}
      </div>
    {:else}
      {#each chart.series as s}
        {@const scale = scaleOf(chart, s)}
        <div class="curve label" style={`--tone: ${toneVar(s.tone)}`}>
          <span class="num">{num(scale.min)}</span>
          <span class="name">{s.name}{s.unit ? `, ${s.unit}` : ""}</span>
          <span class="num">{num(scale.max)}</span>
        </div>
      {/each}
    {/if}
    <div class="plot">
      <Plot {chart} {label} />
    </div>
  </div>
  <div class="axis label num" aria-hidden="true">
    {#each ticks as t}
      <span style={`left: ${t.at}%`} class:last={t.at > 97} class:first={t.at < 3}>{t.label}</span>
    {/each}
  </div>
{/if}

<style>
  .track {
    border: 1px solid var(--ink);
    background: var(--surface);
    min-width: 0;
  }

  /* One header row per curve: scale ends either side of its name, over a rule in its colour. */
  .curve {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.75rem;
    padding: 0.3rem 0.6rem 0.25rem;
    border-bottom: 3px solid var(--tone);
    color: var(--ink);
  }

  .curve.scale {
    border-bottom: 1px solid var(--rule);
  }

  .bands {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: 1fr;
  }

  .band {
    padding: 0.3rem 0.6rem 0.25rem;
    border-bottom: 7px solid var(--tone);
    text-align: center;
    font-weight: 600;
    color: var(--ink);
  }

  .band + .band {
    border-left: 1px solid var(--rule);
  }

  .curve + .curve {
    border-top: 1px solid var(--rule);
  }

  .name {
    text-align: center;
    font-weight: 600;
  }

  .curve .num {
    color: var(--ink-2);
  }

  .plot {
    border-top: 1px solid var(--ink);
    aspect-ratio: 16 / 8;
    max-height: 22rem;
    width: 100%;
  }

  .axis {
    position: relative;
    height: 1.6rem;
    margin-inline: 1px;
  }

  .axis span {
    position: absolute;
    top: 0.3rem;
    transform: translateX(-50%);
    white-space: nowrap;
  }

  .axis span.last {
    transform: translateX(-100%);
  }

  .axis span.first {
    transform: none;
  }

  .bars {
    display: grid;
    grid-template-columns: max-content 1fr 1fr;
    gap: 0 0.75rem;
  }

  .cats {
    display: grid;
  }

  .head-spacer {
    height: calc(1.6rem + 4px);
  }

  .cat {
    display: flex;
    align-items: center;
    color: var(--ink);
    padding-block: 0.35rem;
  }

  .rows {
    display: grid;
    border-top: 1px solid var(--ink);
  }

  .row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding-block: 0.35rem;
  }

  /* The lane is the scale; the value sits outside it so it never clips. */
  .lane {
    flex: 1;
    min-width: 0;
  }

  .bar {
    height: 0.9rem;
    min-width: 1px;
  }

  .value {
    flex: 0 0 3.2rem;
    padding-right: 0.5rem;
    text-align: right;
    color: var(--ink-2);
  }

  .rowcat {
    display: none;
  }

  @media (max-width: 40rem) {
    .bars {
      grid-template-columns: minmax(0, 1fr);
      row-gap: 1rem;
    }

    .cats {
      display: none;
    }

    .rowcat {
      display: block;
      flex: 0 0 7.5rem;
      color: var(--ink);
      padding-left: 0.6rem;
    }
  }
</style>
