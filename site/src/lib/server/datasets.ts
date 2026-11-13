import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { sparkOf } from "$lib/chart";
import { bytes } from "$lib/format";
import { groupInstances } from "$lib/instances";
import type {
  Chart,
  Column,
  DatasetSummary,
  FileSearch,
  Glance,
  GuideStep,
  InstanceGroup,
  Query,
  SeriesChart,
  Snippet,
  Table,
  Upstream,
} from "$lib/types";
import { highlight } from "./highlight";
import { listTree, type TreeTable } from "./tree";

/**
 * The canonical data base: the Hugging Face `main` revision. Glances are written
 * against it (PUBLIC_BASE in scripts/site/glances.py) and it is the default.
 * tests/site/test_glances.py holds this to the Python copies.
 */
const CANONICAL_BASE = "https://huggingface.co/datasets/oskrgab/petrodb/resolve/main";

/**
 * Where visitors read the data from. The deploy sets `BASE_URL` to the deploying
 * branch's Hugging Face base, so a `stage` build names `/resolve/stage/` (ADR-0005).
 */
export const DATA_BASE = (process.env.BASE_URL || CANONICAL_BASE).replace(/\/+$/, "");

/** The Hugging Face repository behind DATA_BASE, for addresses pinned to a commit. */
export const DATA_REPO = DATA_BASE.replace(/\/resolve\/[^/]+$/, "");

/** Catalogue order on the home page. */
export const DATASET_IDS = ["volve", "force_2020", "argentina", "petrobras_3w"];

// Builds run from site/ (pnpm build, pnpm dev); bundled code cannot locate itself.
const SITE_ROOT = process.cwd();
const DATA_ROOT = resolve(SITE_ROOT, "data");
const PARQUET_ROOT = resolve(SITE_ROOT, "../parquet");

function readJson<T>(path: string): T | null {
  return existsSync(path) ? (JSON.parse(readFileSync(path, "utf8")) as T) : null;
}

/** A query as `dataset.json` and `guide.json` write it: `{base}` stands for the data base. */
interface RawQuery {
  id: string;
  title: string;
  sql: string;
  python?: string;
  polars?: string;
}

/** `site/data/<id>/dataset.json`: what a Dataset's pages say, written by hand. */
interface DatasetMeta {
  name: string;
  holds: string;
  grain: string;
  ready: boolean;
  /** The tree is gitignored and built in CI rather than committed (Petrobras 3W). */
  generated?: boolean;
  petroviz: DatasetSummary["petroviz"];
  licence: DatasetSummary["licence"];
  about?: string[];
  units?: { column: string; unit: string }[];
  queries?: (RawQuery & { why: string })[];
  source?: { text: string };
  /** The Multi-parquet table the Instance browser lists by Event class, and its search box. */
  instances?: { table: string; search?: FileSearch };
  /** The search box over a Multi-parquet table's member files. */
  file_search?: FileSearch;
}

const metas = new Map<string, DatasetMeta>();

function readMeta(id: string): DatasetMeta {
  if (!metas.has(id)) {
    const meta = readJson<DatasetMeta>(resolve(DATA_ROOT, id, "dataset.json"));
    if (!meta) throw new Error(`No dataset.json for ${id}`);
    metas.set(id, meta);
  }
  return metas.get(id)!;
}

interface RawGlance {
  id: string;
  title: string;
  takeaway: string;
  sql: string;
  polars?: string;
  chart: Chart;
}

/**
 * A committed Dataset's listing is written by the Glances command. A Dataset
 * whose tree is built in CI (`"generated": true`) is listed from disk at build time.
 */
function listFiles(id: string): TreeTable[] | null {
  if (!listings.has(id)) {
    listings.set(id, readJson<TreeTable[]>(resolve(DATA_ROOT, id, "files.json")) ?? listTree(resolve(PARQUET_ROOT, id)));
  }
  return listings.get(id) ?? null;
}

// Listing 3W reads 2,228 footers; build each listing once.
const listings = new Map<string, TreeTable[] | null>();

/**
 * Whether a Dataset's page can be built here. A generated Dataset's tree is
 * gitignored and rebuilt in CI, so its page exists only where the pipeline has
 * run and left the schema documents the page reads.
 */
function treeOnDisk(id: string, meta: DatasetMeta): boolean {
  return !meta.generated || existsSync(resolve(PARQUET_ROOT, id, "schema.json"));
}

/** Why a Dataset marked ready gets no page in this build, or null if it gets one. */
export function skipReason(id: string): string | null {
  const meta = readMeta(id);
  if (!meta.ready || treeOnDisk(id, meta)) return null;
  return `parquet/${id}/ is not on disk. The ${id} pipeline builds it; CI runs it before the site build.`;
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

/**
 * `{base}` is the data base and `{repo}` its repository, for addresses pinned to
 * a commit. Glances arrive already written against CANONICAL_BASE.
 */
function fill(text: string): string {
  return text
    .replaceAll("{base}", DATA_BASE)
    .replaceAll(CANONICAL_BASE, DATA_BASE)
    .replaceAll("{repo}", DATA_REPO);
}

function snippets(q: Omit<RawQuery, "id" | "title">): Snippet[] {
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

/** The home page catalogue draws a spark from a Dataset's first Glance, left to right. */
function spark(chart: Chart | undefined): SeriesChart | null {
  if (!chart) return null;
  return chart.kind === "log" ? sparkOf(chart) : chart;
}

export function loadSummary(id: string): DatasetSummary {
  const meta = readMeta(id);
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
    ready: meta.ready && treeOnDisk(id, meta),
    petroviz: meta.petroviz,
    licence: meta.licence,
    spark: spark(glances?.[0]?.chart),
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
  const files = listFiles(id) ?? [];
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
      fileCount: file?.files?.length ?? 0,
      files: file?.files ?? [],
    };
  });
}

interface RawGuideStep extends RawQuery {
  body: string[];
  /** Why a variant is absent, by language. */
  missing?: Partial<Record<Snippet["lang"], string>>;
}

/** The "Query the data" guide, steps in teaching order. */
export function loadGuide(): { intro: string[]; steps: GuideStep[] } {
  const raw = readJson<{ intro: string[]; steps: RawGuideStep[] }>(resolve(DATA_ROOT, "guide.json"));
  if (!raw) throw new Error("No guide.json");
  return {
    intro: raw.intro.map(fill),
    steps: raw.steps.map((s) => ({
      id: s.id,
      title: s.title,
      body: s.body.map(fill),
      snippets: snippets(s),
      missing: Object.values(s.missing ?? {}),
    })),
  };
}

export function loadDataset(id: string) {
  const meta = readMeta(id);
  const queries: Query[] = (meta.queries ?? []).map((q) => ({
    id: q.id,
    title: q.title,
    why: q.why,
    snippets: snippets(q),
  }));
  const browsed = meta.instances?.table;
  const listed = loadTables(id);
  const instances = browsed ? instanceGroups(id, listed, browsed) : null;
  // The Instance browser carries the browsed table's files; do not ship them twice.
  const tables = listed.map((t) => (t.name === browsed ? { ...t, files: [] } : t));
  const schema = readJson<{ upstream?: Upstream }>(resolve(PARQUET_ROOT, id, "schema.json"));
  return {
    summary: loadSummary(id),
    about: meta.about ?? [],
    units: meta.units ?? [],
    source: meta.source?.text ?? "",
    glances: loadGlances(id),
    queries,
    tables,
    // The pin the pipeline wrote into schema.json (ADR-0002), never retyped here.
    // Other schemas describe their upstream without pinning a release.
    upstream: schema?.upstream?.git_tag ? schema.upstream : null,
    instances,
    browsed: browsed ?? null,
    fileSearch: meta.file_search ?? {},
    instanceSearch: meta.instances?.search ?? {},
    dataBase: `${DATA_BASE}/${id}`,
  };
}

/**
 * Group the Petrobras 3W Observation files by Event class, from the Event class
 * partition of each Manifest path (ADR-0001). The Event class names are
 * committed by the Glances command, since the build reads no parquet rows.
 */
function instanceGroups(id: string, tables: Table[], table: string): InstanceGroup[] {
  const names = readJson<{ event_class: number; description: string }[]>(
    resolve(DATA_ROOT, id, "event_classes.json"),
  );
  if (!names) throw new Error(`No event_classes.json for ${id}: run \`uv run -m scripts.site.glances\``);
  return groupInstances(names, tables.find((t) => t.name === table)?.files ?? []);
}
