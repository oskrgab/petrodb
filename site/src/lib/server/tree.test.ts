// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { listTree } from "./tree.ts";

const SITE = resolve(import.meta.dirname, "../../..");
const PARQUET = resolve(SITE, "../parquet");

for (const dataset of ["volve", "force_2020", "argentina"]) {
  test(`lists ${dataset}'s tree exactly as the Glances command does`, () => {
    // files.json was written by scripts/site/glances.py, which reads row counts
    // with DuckDB: an independent reading of the same files.
    const committed = JSON.parse(readFileSync(resolve(SITE, "data", dataset, "files.json"), "utf8"));
    assert.deepEqual(listTree(resolve(PARQUET, dataset)), committed);
  });
}

test("a Dataset whose tree is not on disk has no listing", () => {
  assert.equal(listTree(resolve(PARQUET, "no_such_dataset")), null);
});
