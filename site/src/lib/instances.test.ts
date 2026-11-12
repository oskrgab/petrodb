// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";
import { filterInstances } from "./instances.ts";

const groups = [
  { eventClass: 0, description: "Normal Operation", files: [{ instanceId: "WELL-00001_20170201010207", bytes: 1 }] },
  {
    eventClass: 8,
    description: "Hydrate in Production Line",
    files: [
      { instanceId: "WELL-00032_20110830235321", bytes: 1 },
      { instanceId: "SIMULATED_00001", bytes: 1 },
    ],
  },
];

const ids = (out: ReturnType<typeof filterInstances>) => out.flatMap((g) => g.files.map((f) => f.instanceId));

test("no filter keeps every Instance", () => {
  assert.equal(ids(filterInstances(groups, "all", "")).length, 3);
});

test("filters by Event class", () => {
  const out = filterInstances(groups, "8", "");
  assert.deepEqual(out.map((g) => g.eventClass), [8]);
  assert.deepEqual(ids(out), ["WELL-00032_20110830235321", "SIMULATED_00001"]);
});

test("filters by instance_id, ignoring case, and drops empty Event classes", () => {
  const out = filterInstances(groups, "all", " well-00032 ");
  assert.deepEqual(out.map((g) => g.eventClass), [8]);
  assert.deepEqual(ids(out), ["WELL-00032_20110830235321"]);
});

test("combines both filters", () => {
  assert.deepEqual(ids(filterInstances(groups, "0", "SIMULATED")), []);
});
