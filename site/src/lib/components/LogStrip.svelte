<script lang="ts">
  import { curveName, depthTicks, intervalBox, logPath, toneVar } from "$lib/chart";
  import type { LogChart } from "$lib/types";
  import CurveHeader from "./CurveHeader.svelte";

  /*
   * A well-log strip as a geologist reads one: depth increasing downward,
   * one track per curve group with the same header as every other chart,
   * and the interpreted lithology as a coloured column on the right.
   * Prerendered SVG; nothing here needs JavaScript.
   */
  let { chart, label }: { chart: LogChart; label: string } = $props();

  const ticks = $derived(depthTicks(chart));
  const columns = $derived(
    `2.75rem repeat(${chart.tracks.length}, minmax(0, 1fr))${chart.column ? " 4.25rem" : ""}`,
  );
</script>

<div class="strip" role="img" aria-label={label}>
  <div class="frame" style={`grid-template-columns: ${columns}`}>
    <div class="unit label" aria-hidden="true">{chart.depth.unit}</div>
    {#each chart.tracks as track}
      <div class="cell head">
        {#each track.series as s}
          <CurveHeader name={curveName(s)} min={s.min ?? 0} max={s.max ?? 1} tone={s.tone} stack />
        {/each}
      </div>
    {/each}
    {#if chart.column}
      <div class="cell head colhead fine">{chart.column.name}</div>
    {/if}

    <div class="axis label num" aria-hidden="true">
      {#each ticks as t}
        <span style={`top: ${t.at}%`}>{t.label}</span>
      {/each}
    </div>
    {#each chart.tracks as track}
      <div class="cell plot">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          {#each [25, 50, 75] as x}
            <line class="grid" x1={x} x2={x} y1="0" y2="100" />
          {/each}
          {#each ticks as t}
            <line class="grid" x1="0" x2="100" y1={t.at} y2={t.at} />
          {/each}
          {#each track.series as s}
            <path class="line" d={logPath(chart, s)} stroke={toneVar(s.tone)} />
          {/each}
        </svg>
      </div>
    {/each}
    {#if chart.column}
      <div class="cell plot">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          {#each chart.column.intervals as run}
            {@const box = intervalBox(chart, run.top, run.base)}
            <rect x="0" width="100" y={box.y} height={box.height} fill={`var(--lith-${run.key})`} />
          {/each}
        </svg>
      </div>
    {/if}
  </div>

  {#if chart.column}
    <ul class="legend fine" aria-label={`${chart.column.name} classes`}>
      {#each chart.column.classes as c}
        <li><span class="swatch" style={`background: var(--lith-${c.key})`}></span>{c.name}</li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .strip {
    margin: 0;
  }

  .frame {
    display: grid;
    grid-template-rows: auto clamp(26rem, 70vh, 34rem);
  }

  .cell {
    min-width: 0;
    border-left: 1px solid var(--ink);
    background: var(--surface);
  }

  .cell:nth-last-child(1),
  .head:has(+ .axis) {
    border-right: 1px solid var(--ink);
  }

  /* The header's coloured rule sits on the plot, whatever the header's height. */
  .head {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    border-top: 1px solid var(--ink);
  }

  .colhead {
    justify-content: flex-end;
    padding: 0.3rem 0.2rem 0.25rem;
    color: var(--ink);
    font-size: 0.75rem;
    font-weight: 600;
    overflow-wrap: anywhere;
    text-align: center;
    line-height: 1.3;
    border-bottom: 1px solid var(--rule);
  }

  .plot {
    border-top: 1px solid var(--ink);
    border-bottom: 1px solid var(--ink);
  }

  .unit {
    align-self: end;
    padding: 0 0.4rem 0.25rem 0;
    text-align: right;
  }

  .axis {
    position: relative;
  }

  .axis span {
    position: absolute;
    right: 0.4rem;
    transform: translateY(-50%);
    white-space: nowrap;
  }

  svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  rect {
    shape-rendering: crispEdges;
  }

  .grid {
    stroke: var(--grid);
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }

  .line {
    fill: none;
    stroke-width: 1.25;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 1rem;
    list-style: none;
    margin: 0.6rem 0 0 2.75rem;
    padding: 0;
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .swatch {
    width: 0.9rem;
    height: 0.9rem;
    border: 1px solid var(--rule);
  }
</style>
