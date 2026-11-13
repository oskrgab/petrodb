// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";
import { linkEvent, track, type AnalyticsWindow, type EventData } from "./analytics.ts";

const ORIGIN = "https://petrodb.ocortez.com";

function fakeWindow(loaded: boolean, readyState: DocumentReadyState) {
  const sent: [string, EventData | undefined][] = [];
  const onLoad: (() => void)[] = [];
  const umami = { track: (name: string, data?: EventData) => sent.push([name, data]) };
  const win: { umami?: typeof umami } & AnalyticsWindow = {
    umami: loaded ? umami : undefined,
    document: { readyState },
    addEventListener: (_type, listener) => onLoad.push(listener),
  };
  return { win, sent, onLoad, umami };
}

test("an event goes to the tracker once it has loaded", () => {
  const { win, sent } = fakeWindow(true, "complete");
  track("copy-snippet", { lang: "python" }, win);
  assert.deepEqual(sent, [["copy-snippet", { lang: "python" }]]);
});

test("an event ready before the tracker waits for the page to load", () => {
  const { win, sent, onLoad, umami } = fakeWindow(false, "interactive");
  track("copy-snippet", { lang: "python" }, win);
  assert.deepEqual(sent, []);
  win.umami = umami;
  onLoad.forEach((listener) => listener());
  assert.deepEqual(sent, [["copy-snippet", { lang: "python" }]]);
});

test("a page that loaded without the tracker drops the event", () => {
  const { win, sent, onLoad } = fakeWindow(false, "complete");
  track("copy-snippet", { lang: "python" }, win);
  assert.deepEqual(sent, []);
  assert.deepEqual(onLoad, []);
});

test("a data file is open-file with its path in the published tree, whatever the revision", () => {
  const expected = { name: "open-file", data: { file: "volve/wells.parquet" } };
  for (const rev of ["main", "stage"]) {
    const href = `https://huggingface.co/datasets/oskrgab/petrodb/resolve/${rev}/volve/wells.parquet`;
    assert.deepEqual(linkEvent(href, ORIGIN), expected);
  }
  // The dev host serves the data beside the Landing.
  assert.deepEqual(linkEvent("/volve/wells.parquet", ORIGIN), expected);
});

test("a manifest or schema document is open-file too", () => {
  assert.deepEqual(linkEvent("schema.md", `${ORIGIN}/argentina/`)?.name, "open-file");
  assert.deepEqual(linkEvent(`${ORIGIN}/argentina/schema.md`, ORIGIN)?.data, { file: "argentina/schema.md" });
  assert.deepEqual(
    linkEvent("https://huggingface.co/datasets/oskrgab/petrodb/resolve/main/force_2020/wells/_files.json", ORIGIN)?.data,
    { file: "force_2020/wells/_files.json" },
  );
});

test("a link off the Landing is outbound, named by host and path", () => {
  assert.deepEqual(linkEvent("https://petroviz.ocortez.com/", ORIGIN), {
    name: "outbound",
    data: { to: "petroviz.ocortez.com" },
  });
  assert.deepEqual(linkEvent("https://github.com/oskrgab/petrodb?tab=readme#top", ORIGIN), {
    name: "outbound",
    data: { to: "github.com/oskrgab/petrodb" },
  });
});

test("a link to another Landing page is no event: the tracker counts the page view", () => {
  assert.equal(linkEvent("/query/", ORIGIN), null);
  assert.equal(linkEvent(`${ORIGIN}/volve/#files`, ORIGIN), null);
  assert.equal(linkEvent("mailto:someone@example.com", ORIGIN), null);
});
