import type { LogChart, Series, SeriesChart } from "./types";

/** Plots are drawn in a 0–100 box and stretched to fit; strokes do not scale. */
const SIZE = 100;

function xAt(i: number, n: number): number {
  return n > 1 ? (i / (n - 1)) * SIZE : SIZE / 2;
}

function yAt(v: number, min: number, max: number): number {
  return SIZE - ((v - min) / (max - min)) * SIZE;
}

const fmt = (n: number) => n.toFixed(2);

/** A polyline path; nulls lift the pen. */
export function linePath(s: Series, min: number, max: number): string {
  const n = s.values.length;
  let d = "";
  let pen = false;
  s.values.forEach((v, i) => {
    if (v == null) {
      pen = false;
      return;
    }
    d += `${pen ? "L" : "M"}${fmt(xAt(i, n))} ${fmt(yAt(v, min, max))}`;
    pen = true;
  });
  return d;
}

/** Closed bands for a stacked area chart, first series at the bottom. */
export function stackPaths(chart: SeriesChart): string[] {
  const n = chart.x.values.length;
  const min = chart.min ?? 0;
  const max = chart.max ?? 1;
  const base = new Array(n).fill(0);
  return chart.series.map((s) => {
    const top = s.values.map((v, i) => base[i] + (v ?? 0));
    let d = "";
    top.forEach((v, i) => (d += `${i ? "L" : "M"}${fmt(xAt(i, n))} ${fmt(yAt(v, min, max))}`));
    for (let i = n - 1; i >= 0; i--) d += `L${fmt(xAt(i, n))} ${fmt(yAt(base[i], min, max))}`;
    top.forEach((v, i) => (base[i] = v));
    return d + "Z";
  });
}

export interface Tick {
  /** Position along the axis, 0–100. */
  at: number;
  label: string;
}

/** Axis ticks at round values of whatever the x axis measures. */
export function xTicks(chart: SeriesChart): Tick[] {
  const { type, values } = chart.x;
  const n = values.length;
  const ticks: Tick[] = [];
  values.forEach((v, i) => {
    let label: string | null = null;
    if (type === "year" && Number(v) % 5 === 0) label = String(v);
    if (type === "month" && String(v).endsWith("-01")) label = String(v).slice(0, 4);
    if (type === "depth" && Number(v) % 500 === 0) label = `${Number(v).toLocaleString("en-US")} m`;
    if (type === "time") {
      const t = new Date(`${v}Z`);
      if (t.getUTCMinutes() === 0 && t.getUTCHours() % 6 === 0) {
        label = `${String(t.getUTCHours()).padStart(2, "0")}:00`;
      }
    }
    if (label) ticks.push({ at: xAt(i, n), label });
  });
  return ticks;
}

export function scaleOf(chart: SeriesChart, s: Series): { min: number; max: number } {
  return { min: s.min ?? chart.min ?? 0, max: s.max ?? chart.max ?? 1 };
}

export function toneVar(tone: Series["tone"]): string {
  return `var(--${tone})`;
}

/* Well-log strips: depth runs down the plot, values across it. */

function depthAt(d: number, chart: LogChart): number {
  const { min, max } = chart.depth;
  return ((d - min) / (max - min)) * SIZE;
}

/** A curve down a log track; nulls lift the pen. Off-scale values are clipped by the track. */
export function logPath(chart: LogChart, s: Series): string {
  const min = s.min ?? 0;
  const max = s.max ?? 1;
  let d = "";
  let pen = false;
  s.values.forEach((v, i) => {
    if (v == null) {
      pen = false;
      return;
    }
    const x = ((v - min) / (max - min)) * SIZE;
    d += `${pen ? "L" : "M"}${fmt(x)} ${fmt(depthAt(chart.depth.values[i], chart))}`;
    pen = true;
  });
  return d;
}

/** A column interval as a box in the 0–100 plot. */
export function intervalBox(chart: LogChart, top: number, base: number): { y: number; height: number } {
  const y = depthAt(top, chart);
  return { y, height: depthAt(base, chart) - y };
}

/** Depth ticks every 500 m, positioned 0–100 from the top of the strip. */
export function depthTicks(chart: LogChart): Tick[] {
  const ticks: Tick[] = [];
  const step = 500;
  for (let d = Math.ceil(chart.depth.min / step) * step; d <= chart.depth.max; d += step) {
    ticks.push({ at: depthAt(d, chart), label: d.toLocaleString("en-US") });
  }
  return ticks;
}

/** A curve's header label: its name, then its unit. */
export function curveName(s: Series): string {
  return `${s.name}${s.unit ? `, ${s.unit}` : ""}`;
}

/** A log strip's first curve laid on its side, for the home page's catalogue spark. */
export function sparkOf(chart: LogChart): SeriesChart {
  return {
    kind: "lines",
    x: { type: "depth", values: chart.depth.values },
    series: [chart.tracks[0].series[0]],
  };
}
