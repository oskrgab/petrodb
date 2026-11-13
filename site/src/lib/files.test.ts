// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";
import { filterFiles, shownCount } from "./files.ts";

const wells = [
  { name: "15-9-13.parquet", href: "a", bytes: 1 },
  { name: "16-11-1_ST3.parquet", href: "b", bytes: 1 },
  { name: "35-11-1.parquet", href: "c", bytes: 1 },
];
// FORCE 2020 well names are typed with "/" and a space; the files spell them "-" and "_".
const spellings: [string, string][] = [
  ["/", "-"],
  [" ", "_"],
];
const names = (out: typeof wells) => out.map((f) => f.name);

test("an empty search keeps every file", () => {
  assert.deepEqual(names(filterFiles(wells, "  ", spellings)), names(wells));
});

test("matches the files' spelling of what was typed, ignoring case", () => {
  assert.deepEqual(names(filterFiles(wells, "15/9-13", spellings)), ["15-9-13.parquet"]);
  assert.deepEqual(names(filterFiles(wells, "16/11-1  st3", spellings)), ["16-11-1_ST3.parquet"]);
});

test("without spellings a search matches the names as they are", () => {
  assert.deepEqual(names(filterFiles(wells, "15/9", [])), []);
  assert.deepEqual(names(filterFiles(wells, "-11-", [])), ["16-11-1_ST3.parquet", "35-11-1.parquet"]);
});

test("counts what is shown against the whole", () => {
  assert.equal(shownCount(3, 3, "files"), "3 files");
  assert.equal(shownCount(1, 2228, "Instances"), "1 of 2,228 Instances");
});
