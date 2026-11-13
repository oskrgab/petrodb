// Copy each Dataset's schema documents from ../parquet into static/, so they
// are served beside the dataset page at the paths they have always had
// (/argentina/schema.md, ...). The copies are build inputs, not sources.
import { cpSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

const DOCS = ["schema.md", "schema.json", "schema.sql", "README.md"];
const parquet = resolve(process.cwd(), "../parquet");

for (const entry of readdirSync(parquet, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  for (const doc of DOCS) {
    const from = resolve(parquet, entry.name, doc);
    if (!existsSync(from)) continue;
    const to = resolve(process.cwd(), "static", entry.name);
    mkdirSync(to, { recursive: true });
    cpSync(from, resolve(to, doc));
  }
}
