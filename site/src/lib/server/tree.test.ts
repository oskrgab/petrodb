// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { copyFileSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { test } from "node:test";
import { listDataset, listTree, type TreeTable } from "./tree.ts";

const SITE = resolve(import.meta.dirname, "../../..");
const PARQUET = resolve(SITE, "../parquet");

for (const dataset of ["volve", "force_2020", "argentina"]) {
  test(`lists ${dataset}'s tree exactly as the Glances command does`, () => {
    // files.json was written by scripts/site/glances.py, which reads row counts
    // with DuckDB: an independent reading of the same files.
    // Tables built in CI are not in files.json, whether or not a local build
    // left them on disk.
    const committed = JSON.parse(readFileSync(resolve(SITE, "data", dataset, "files.json"), "utf8"));
    const generated: string[] = JSON.parse(
      readFileSync(resolve(SITE, "data", dataset, "dataset.json"), "utf8"),
    ).generated_tables ?? [];
    const listed = listTree(resolve(PARQUET, dataset))!.filter((t) => !generated.includes(t.name));
    assert.deepEqual(listed, committed);
  });
}

test("a Dataset whose tree is not on disk has no listing", () => {
  assert.equal(listTree(resolve(PARQUET, "no_such_dataset")), null);
});

// The Volve log tables are gitignored and built in CI before the site build.
const GENERATED = ["petrophysical_interpretation", "log_curves"];
const committedVolve = (): TreeTable[] =>
  JSON.parse(readFileSync(resolve(SITE, "data", "volve", "files.json"), "utf8"));

test("a committed listing gains the tables built in CI that are on disk", () => {
  const root = mkdtempSync(resolve(tmpdir(), "petrodb-tree-"));
  const wells = resolve(PARQUET, "volve", "wells.parquet");
  copyFileSync(wells, resolve(root, "log_curves.parquet"));
  copyFileSync(wells, resolve(root, "stray.parquet"));
  const listed = listDataset(root, committedVolve(), GENERATED)!;
  const added = listed.find((t) => t.name === "log_curves");
  assert.deepEqual(added, {
    name: "log_curves",
    kind: "single",
    path: "log_curves.parquet",
    bytes: readFileSync(wells).length,
    rows: 27,
  });
  // Not on disk, so not listed; a file that is neither committed nor generated is ignored.
  assert.deepEqual(
    listed.map((t) => t.name),
    ["daily_production", "monthly_production", "wells", "log_curves"],
  );
});

test("a committed listing is unchanged when no table built in CI is on disk", () => {
  const root = mkdtempSync(resolve(tmpdir(), "petrodb-tree-"));
  assert.deepEqual(listDataset(root, committedVolve(), GENERATED), committedVolve());
});

test("a Dataset with no committed listing is listed from disk whole", () => {
  assert.deepEqual(listDataset(resolve(PARQUET, "volve"), null, []), listTree(resolve(PARQUET, "volve")));
});
