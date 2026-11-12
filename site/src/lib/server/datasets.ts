import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { bytes } from "$lib/format";
import type { Chart, Column, DatasetSummary, Glance, Query, Snippet, Table, TableFile } from "$lib/types";
import { highlight } from "./highlight";

/**
 * The canonical data base: the Hugging Face `main` revision. Glances are written
 * against it (PUBLIC_BASE in scripts/site/glances.py) and it is the default.
 */
const CANONICAL_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/main";

/**
 * Where visitors read the data from. The deploy sets `BASE_URL` to the deploying
 * branch's Hugging Face base, so a `stage` build names `/resolve/stage/` (ADR-0005).
 */
export const DATA_BASE = (process.env.BASE_URL || CANONICAL_BASE).replace(/\/+$/, "");

/** Catalogue order on the home page. */
export const DATASET_IDS = ["volve", "force_2020", "argentina", "petrobras_3w"];

// Builds run from site/ (pnpm build, pnpm dev); bundled code cannot locate itself.
const SITE_ROOT = process.cwd();
const DATA_ROOT = resolve(SITE_ROOT, "data");
const PARQUET_ROOT = resolve(SITE_ROOT, "../parquet");

function readJson<T>(path: string): T | null {
  return existsSync(path) ? (JSON.parse(readFileSync(path, "utf8")) as T) : null;
}

interface RawGlance {
  id: string;
  title: string;
  takeaway: string;
  sql: string;
  polars?: string;
  chart: Chart;
}

interface RawFiles {
  name: string;
  kind: "single" | "multi";
  path?: string;
  manifest?: string;
  bytes: number;
  rows: number;
  files?: TableFile[];
}

/** Wrap a DuckDB SQL script so it runs from Python and returns a DataFrame. */
function sqlToPython(sql: string): string {
  const body = sql
    .replace(/;\s*$/, "")
    .split("\n")
    .map((line) => (line ? `    ${line}` : line))
    .join("\n");
  return `import duckdb\n\ndf = duckdb.sql("""\n${body}\n""").df()`;
}

function snippets(q: { sql: string; python?: string; polars?: string }): Snippet[] {
  const fill = (code: string) => code.replaceAll("{base}", DATA_BASE).replaceAll(CANONICAL_BASE, DATA_BASE);
  const sql = fill(q.sql);
  const python = q.python ? fill(q.python) : sqlToPython(sql);
  const out: Snippet[] = [
    { lang: "sql", label: "DuckDB SQL", code: sql, html: highlight(sql, "sql") },
    { lang: "python", label: "Python", code: python, html: highlight(python, "python") },
  ];
  if (q.polars) {
    const polars = fill(q.polars);
    out.push({ lang: "polars", label: "Polars", code: polars, html: highlight(polars, "python") });
  }
  return out;
}

export function loadGlances(id: string): Glance[] {
  const raw = readJson<RawGlance[]>(resolve(DATA_ROOT, id, "glances.json")) ?? [];
  return raw.map((g) => ({
    id: g.id,
    title: g.title,
    takeaway: g.takeaway,
    chart: g.chart,
    snippets: snippets(g),
  }));
}

export function loadSummary(id: string): DatasetSummary {
  const meta = readJson<Record<string, any>>(resolve(DATA_ROOT, id, "dataset.json"));
  if (!meta) throw new Error(`No dataset.json for ${id}`);
  // Computed from the data by scripts/site/glances.py; never typed by hand.
  const facts = readJson<{ covers: string; bytes: number }>(resolve(DATA_ROOT, id, "facts.json"));
  if (!facts) throw new Error(`No facts.json for ${id}: run \`uv run -m scripts.site.glances ${id}\``);
  const glances = readJson<RawGlance[]>(resolve(DATA_ROOT, id, "glances.json"));
  return {
    id,
    name: meta.name,
    holds: meta.holds,
    grain: meta.grain,
    covers: facts.covers,
    size: bytes(facts.bytes),
    ready: meta.ready,
    petroviz: meta.petroviz,
    licence: meta.licence,
    spark: glances?.[0]?.chart ?? null,
  };
}

/**
 * Column descriptions live only in the generated schema.md, as one Markdown
 * table per `### \`table\`` heading. Returns table → column → description.
 */
function columnDescriptions(markdown: string): Map<string, Map<string, string>> {
  const out = new Map<string, Map<string, string>>();
  let current: Map<string, string> | null = null;
  for (const line of markdown.split("\n")) {
    const heading = line.match(/^### `([^`]+)`/);
    if (heading) {
      current = new Map();
      out.set(heading[1], current);
      continue;
    }
    if (line.startsWith("## ")) current = null;
    const row = line.match(/^\| `([^`]+)` \|(.*)\|\s*$/);
    if (row && current) {
      const cells = row[2].split("|");
      current.set(row[1], cells[cells.length - 1].trim());
    }
  }
  return out;
}

/** Inline Markdown in schema text: `code` and *emphasis* only. */
export function inlineMarkdown(text: string): string {
  const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

export function loadTables(id: string): Table[] {
  const schema = readJson<{ tables: Record<string, any> }>(resolve(PARQUET_ROOT, id, "schema.json"));
  const files = readJson<RawFiles[]>(resolve(DATA_ROOT, id, "files.json")) ?? [];
  if (!schema) return [];
  const mdPath = resolve(PARQUET_ROOT, id, "schema.md");
  const described = columnDescriptions(existsSync(mdPath) ? readFileSync(mdPath, "utf8") : "");

  return Object.entries(schema.tables).map(([name, t]) => {
    const file = files.find((f) => f.name === name);
    const columns: Column[] = t.columns.map((c: any) => ({
      name: c.name,
      type: c.type,
      key: Boolean(c.primary_key),
      description: inlineMarkdown(described.get(name)?.get(c.name) ?? ""),
    }));
    return {
      name,
      description: inlineMarkdown(t.description ?? ""),
      columns,
      references: (t.foreign_keys ?? []).map(
        (fk: any) => `${fk.column} → ${fk.references_table}.${fk.references_column}`,
      ),
      kind: file?.kind ?? "single",
      path: file?.path,
      manifest: file?.manifest,
      bytes: file?.bytes ?? 0,
      rows: file?.rows ?? 0,
      files: file?.files ?? [],
    };
  });
}

export function loadDataset(id: string) {
  const meta = readJson<Record<string, any>>(resolve(DATA_ROOT, id, "dataset.json"));
  if (!meta) throw new Error(`No dataset.json for ${id}`);
  const queries: Query[] = (meta.queries ?? []).map((q: any) => ({
    id: q.id,
    title: q.title,
    why: q.why,
    snippets: snippets(q),
  }));
  return {
    summary: loadSummary(id),
    about: (meta.about ?? []) as string[],
    units: (meta.units ?? []) as { column: string; unit: string }[],
    source: (meta.source?.text ?? "") as string,
    glances: loadGlances(id),
    queries,
    tables: loadTables(id),
    dataBase: `${DATA_BASE}/${id}`,
  };
}
