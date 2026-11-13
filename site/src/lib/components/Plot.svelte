<script lang="ts">
  import { linePath, scaleOf, spanBox, stackPaths, toneVar, xTicks } from "$lib/chart";
  import type { SeriesChart } from "$lib/types";

  let { chart, grid = true, label }: { chart: SeriesChart; grid?: boolean; label: string } = $props();

  const ticks = $derived(xTicks(chart));
</script>

<svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={label}>
  {#if grid}
    {#each [25, 50, 75] as y}
      <line class="grid" x1="0" x2="100" y1={y} y2={y} />
    {/each}
    {#each ticks as t}
      <line class="grid" x1={t.at} x2={t.at} y1="0" y2="100" />
    {/each}
  {/if}

  {#each chart.spans ?? [] as s, i}
    {@const at = spanBox(chart, s)}
    <rect class="span" class:strong={i > 0} x={at.x} width={at.width} y="0" height="100" />
  {/each}

  {#if chart.kind === "stacked"}
    {#each stackPaths(chart) as d, i}
      <path {d} fill={toneVar(chart.series[i].tone)} />
    {/each}
  {:else}
    {#each chart.series as s}
      {@const scale = scaleOf(chart, s)}
      <path class="line" d={linePath(s, scale.min, scale.max)} stroke={toneVar(s.tone)} />
    {/each}
  {/if}
</svg>

<style>
  svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  .grid {
    stroke: var(--grid);
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }

  /* Labelled stretches sit behind the curves: the first faint, later ones stronger. */
  .span {
    fill: var(--accent-soft);
  }

  .span.strong {
    fill: var(--accent);
    fill-opacity: 0.28;
  }

  .line {
    fill: none;
    stroke-width: 1.75;
    stroke-linejoin: round;
    stroke-linecap: round;
    vector-effect: non-scaling-stroke;
  }
</style>
