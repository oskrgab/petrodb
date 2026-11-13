import { count } from "./format.ts";
import type { FileSearch } from "./types.ts";

type Spellings = NonNullable<FileSearch["spellings"]>;

/** Text as a search compares it: trimmed, lower-cased, typed spellings swapped for the files'. */
function fold(text: string, spellings: Spellings): string {
  let out = text.trim().toLowerCase().replace(/\s+/g, " ");
  for (const [typed, filed] of spellings) out = out.replaceAll(typed.toLowerCase(), filed.toLowerCase());
  return out;
}

/** Whether `name` contains what was typed in `search`. An empty search matches everything. */
export function matches(name: string, search: string, spellings: Spellings = []): boolean {
  return fold(name, spellings).includes(fold(search, spellings));
}

/** The files whose name contains what was typed in `search`. */
export function filterFiles<T extends { name: string }>(files: T[], search: string, spellings: Spellings = []): T[] {
  return files.filter((f) => matches(f.name, search, spellings));
}

/** "3 files" when every one is shown, "1 of 3 files" when a search narrows them. */
export function shownCount(shown: number, total: number, noun: string): string {
  return shown === total ? `${count(total)} ${noun}` : `${count(shown)} of ${count(total)} ${noun}`;
}
