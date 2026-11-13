export type Tone = "oil" | "oil-2" | "gas" | "water" | "neutral" | "ink";

export interface Series {
  name: string;
  unit?: string;
  tone: Tone;
  min?: number;
  max?: number;
  values: (number | null)[];
}

/** A chart drawn left to right along an x axis. */
export interface SeriesChart {
  kind: "lines" | "stacked" | "bars";
  unit?: string;
  min?: number;
  max?: number;
  x: { type: "month" | "year" | "depth" | "time" | "category"; values: (string | number)[] };
  series: Series[];
  /** Labelled stretches of the x axis, as inclusive indices into x.values. */
  spans?: { name: string; from: number; to: number }[];
}

/** One run of a single class down a categorical column, top above base. */
export interface Interval {
  top: number;
  base: number;
  /** Names the colour token, `--lith-<key>`. */
  key: string;
}

/**
 * A well-log strip: depth runs downward, curves sit side by side in tracks
 * that share the depth axis, and a categorical column (lithology) beside them.
 */
export interface LogChart {
  kind: "log";
  depth: { unit: string; min: number; max: number; values: number[] };
  tracks: { series: Series[] }[];
  column?: { name: string; classes: { key: string; name: string }[]; intervals: Interval[] };
}

export type Chart = SeriesChart | LogChart;

/** One language's version of a query, already highlighted to HTML. */
export interface Snippet {
  lang: "sql" | "python" | "polars";
  label: string;
  code: string;
  html: string;
}

export interface Glance {
  id: string;
  title: string;
  takeaway: string;
  chart: Chart;
  snippets: Snippet[];
}

export interface Query {
  id: string;
  title: string;
  why: string;
  snippets: Snippet[];
}

/** One step of the "Query the data" guide. */
export interface GuideStep {
  id: string;
  title: string;
  body: string[];
  snippets: Snippet[];
  /** Why a language has no variant here, one sentence each. */
  missing: string[];
}

export interface Column {
  name: string;
  type: string;
  key: boolean;
  description: string;
}

/** One member file of a Multi-parquet table; `path` is relative to the Dataset root. */
export interface TableFile {
  path: string;
  bytes: number;
  rows: number;
}

/** A file as a list shows it: a label, the address it links to, its size. */
export interface FileLink {
  name: string;
  href: string;
  bytes: number;
}

/**
 * How a search box reads what a visitor types, from the Dataset's metadata.
 * Both what is typed and the file names are lower-cased before comparing.
 */
export interface FileSearch {
  /** An example of what to type, shown in the empty box. */
  placeholder?: string;
  /**
   * Pairs of [as typed, as the file names spell it]. FORCE 2020 well names are
   * typed "16/11-1 ST3" and spelled "16-11-1_ST3": `[["/", "-"], [" ", "_"]]`.
   */
  spellings?: [string, string][];
}

export interface Table {
  name: string;
  description: string;
  columns: Column[];
  references: string[];
  kind: "single" | "multi";
  path?: string;
  manifest?: string;
  bytes: number;
  rows: number;
  /** How many member files; `files` is left empty when a browser lists them instead. */
  fileCount: number;
  files: TableFile[];
}

export interface DatasetSummary {
  id: string;
  name: string;
  holds: string;
  grain: string;
  covers: string;
  size: string;
  ready: boolean;
  petroviz: { label: string; url: string } | null;
  licence: { name: string; url: string; note?: string };
  spark: SeriesChart | null;
}

/** The upstream release a Dataset is pinned to, as its schema.json records it. */
export interface Upstream {
  repo: string;
  git_tag: string;
  dataset_version: string;
}

/** One Event class's Observation files, for the Petrobras 3W Instance browser. */
export interface InstanceGroup {
  eventClass: number;
  description: string;
  /** `path` is the Manifest's, from the Dataset root; `name` is its file name without `.parquet`. */
  files: { name: string; path: string; bytes: number }[];
}
