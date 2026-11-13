<script lang="ts">
  import { toneVar } from "$lib/chart";
  import { count } from "$lib/format";
  import type { Tone } from "$lib/types";

  /*
   * The header row of a well-log track: the curve's name between the two
   * ends of its scale, over a rule in its colour. Without a tone it states a
   * shared scale over a thin rule. `stack` puts the name on its own line, for
   * tracks too narrow to hold all three side by side; inside a `track`
   * container it does so on its own once the container is narrow.
   */
  let {
    name,
    min,
    max,
    tone,
    stack = false,
  }: { name: string; min: number; max: number; tone?: Tone; stack?: boolean } = $props();
</script>

<div class="curve label" class:scale={!tone} class:stack style={tone ? `--tone: ${toneVar(tone)}` : undefined}>
  <span class="num">{count(min)}</span>
  <span class="name">{name}</span>
  <span class="num">{count(max)}</span>
</div>

<style>
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

  /* Headers stack at the top of their track; rule between consecutive ones. */
  .curve:not(:first-child) {
    border-top: 1px solid var(--rule);
  }

  .name {
    text-align: center;
    font-weight: 600;
  }

  .num {
    color: var(--ink-2);
  }

  .stack {
    flex-wrap: wrap;
    gap: 0 0.5rem;
    padding-inline: 0.4rem;
  }

  .stack .name {
    order: -1;
    flex: 1 0 100%;
    line-height: 1.3;
  }

  /* A bars track (a `track` container) stacks its header once it gets this narrow. */
  @container track (max-width: 9rem) {
    .curve {
      flex-wrap: wrap;
      gap: 0 0.5rem;
      padding-inline: 0.4rem;
    }

    .name {
      order: -1;
      flex: 1 0 100%;
      line-height: 1.3;
    }
  }
</style>
