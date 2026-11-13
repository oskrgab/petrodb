// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";
import { filterInstances, groupInstances, hiveValue } from "./instances.ts";

const file = (path: string) => ({ path, bytes: 1, rows: 1 });

const groups = groupInstances(
  [
    { event_class: 0, description: "Normal Operation" },
    { event_class: 8, description: "Hydrate in Production Line" },
  ],
  [
    file("observations/event_class=0/WELL-00001_20170201010207.parquet"),
    file("observations/event_class=8/WELL-00032_20110830235321.parquet"),
    file("observations/event_class=8/SIMULATED_00001.parquet"),
  ],
);

const ids = (out: ReturnType<typeof filterInstances>) => out.flatMap((g) => g.files.map((f) => f.name));

test("reads a Hive partition value from the folder segments of a Manifest path", () => {
  assert.equal(hiveValue("observations/event_class=8/x.parquet", "event_class"), "8");
  assert.equal(hiveValue("monthly_production/anio=2006/data.parquet", "anio"), "2006");
  assert.equal(hiveValue("wells/15-9-13.parquet", "event_class"), null);
  // A leaf file name is not a partition, whatever it is called.
  assert.equal(hiveValue("observations/event_class=9.parquet", "event_class"), null);
});

test("groups files by Event class and keeps each Manifest path as listed", () => {
  assert.deepEqual(
    groups.map((g) => [g.eventClass, g.files.map((f) => f.path)]),
    [
      [0, ["observations/event_class=0/WELL-00001_20170201010207.parquet"]],
      [8, ["observations/event_class=8/WELL-00032_20110830235321.parquet", "observations/event_class=8/SIMULATED_00001.parquet"]],
    ],
  );
  assert.deepEqual(ids(groups), ["WELL-00001_20170201010207", "WELL-00032_20110830235321", "SIMULATED_00001"]);
});

test("a file outside a known Event class is an error", () => {
  assert.throws(() => groupInstances([{ event_class: 0, description: "Normal" }], [file("observations/event_class=3/x.parquet")]));
  assert.throws(() => groupInstances([{ event_class: 0, description: "Normal" }], [file("observations/x.parquet")]));
});

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
