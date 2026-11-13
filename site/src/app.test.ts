// Run with `pnpm test` (node --test, no dependencies).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

// The Umami loader in app.html.
const html = readFileSync(new URL("./app.html", import.meta.url), "utf8");
const PLACEHOLDER = "%sveltekit.env.PUBLIC_UMAMI_WEBSITE_ID%";
const loader = html.match(/<script data-website-id="([^"]*)">([\s\S]*?)<\/script>/);

/** Run the loader as a browser would, with `id` as the build's website id. */
function load(id: string) {
  assert.ok(loader, "no <script data-website-id=…> loader in app.html");
  const added: Record<string, string>[] = [];
  const document = {
    currentScript: { getAttribute: () => id },
    createElement: () => {
      const attributes: Record<string, string> = {};
      return { attributes, setAttribute: (k: string, v: string) => (attributes[k] = v) };
    },
    head: { appendChild: (el: { attributes: Record<string, string> }) => added.push(el.attributes) },
  };
  vm.runInNewContext(loader[2], { document });
  return added;
}

test("the website id comes from the build, not the repo", () => {
  assert.equal(loader?.[1], PLACEHOLDER);
  assert.doesNotMatch(html, /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/);
});

test("a build without a website id loads no tracker", () => {
  assert.deepEqual(load(""), []);
});

test("the tracker counts the production hostnames only", () => {
  const added = load("some-website-id");
  assert.equal(added.length, 1);
  const [tracker] = added;
  assert.equal(tracker.src, "https://analytics.ocortez.com/script.js");
  assert.equal(tracker["data-website-id"], "some-website-id");
  assert.deepEqual(tracker["data-domains"].split(","), ["petrodb.ocortez.com", "petrodb.pages.dev"]);
});
