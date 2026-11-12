export type Tone = "oil" | "oil-2" | "gas" | "water" | "neutral" | "ink";

export interface Series {
  name: string;
  unit?: string;
  tone: Tone;
  min?: number;
  max?: number;
  values: (number | null)[];
}

export interface Chart {
  kind: "lines" | "stacked" | "bars";
  unit?: string;
  min?: number;
  max?: number;
  x: { type: "month" | "year" | "depth" | "time" | "category"; values: (string | number)[] };
  series: Series[];
}

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

export interface TableFile {
  path: string;
  bytes: number;
  rows: number;
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
  spark: Chart | null;
}
