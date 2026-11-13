// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fullWidth } from "./chart.ts";
import type { Chart } from "./types.ts";

const glances = (id: string): { title: string; chart: Chart }[] =>
  JSON.parse(readFileSync(new URL(`../../data/${id}/glances.json`, import.meta.url), "utf8"));

const bars = (n: number): Chart => ({
  kind: "bars",
  x: { type: "category", values: ["a", "b"] },
  series: Array.from({ length: n }, (_, i) => ({ name: `s${i}`, tone: "oil" as const, values: [1, 2] })),
});

test("bars with three or more series take the whole width; two or fewer share it", () => {
  assert.equal(fullWidth(bars(1)), false);
  assert.equal(fullWidth(bars(2)), false);
  assert.equal(fullWidth(bars(3)), true);
});

test("of the committed Glances, only 3W's real, simulated and hand-drawn bars take the whole width", () => {
  const wide = ["volve", "force_2020", "argentina", "petrobras_3w"].flatMap((id) =>
    glances(id).filter((g) => fullWidth(g.chart)).map((g) => `${id}: ${g.title}`),
  );
  assert.deepEqual(wide, ["petrobras_3w: Real, simulated and hand-drawn"]);
});
