import { matches } from "./files.ts";
import type { FileSearch, InstanceGroup, TableFile } from "./types.ts";

/**
 * The value of Hive partition `key` in a Manifest path: its `key=value/` folder
 * segment, where the partition column lives (ADR-0004). Null when the path has
 * no such folder. The file name itself is never read.
 */
export function hiveValue(path: string, key: string): string | null {
  const folder = path.split("/").slice(0, -1).find((segment) => segment.startsWith(`${key}=`));
  return folder ? folder.slice(key.length + 1) : null;
}

/**
 * Group the Petrobras 3W Observation files by Event class, in the order of
 * `classes`, keeping each file's Manifest path as listed. The Event class is
 * the `event_class` partition of the path.
 */
export function groupInstances(
  classes: { event_class: number; description: string }[],
  files: TableFile[],
): InstanceGroup[] {
  const groups: InstanceGroup[] = classes.map((c) => ({
    eventClass: c.event_class,
    description: c.description,
    files: [],
  }));
  for (const f of files) {
    const value = hiveValue(f.path, "event_class");
    const group = value === null ? undefined : groups.find((g) => String(g.eventClass) === value);
    if (!group) throw new Error(`${f.path} is not in an event_class=N/ partition of a known Event class`);
    const name = f.path.slice(f.path.lastIndexOf("/") + 1).replace(/\.parquet$/, "");
    group.files.push({ name, path: f.path, bytes: f.bytes });
  }
  return groups;
}

/**
 * The Instance browser's filter: keep one Event class ("all" keeps every one)
 * and the Instances whose name (their `instance_id`) contains `search`,
 * read as `matches` reads it. Groups left empty are dropped.
 */
export function filterInstances(
  groups: InstanceGroup[],
  eventClass: string,
  search: string,
  spellings: FileSearch["spellings"] = [],
): InstanceGroup[] {
  return groups
    .filter((g) => eventClass === "all" || String(g.eventClass) === eventClass)
    .map((g) => ({ ...g, files: g.files.filter((f) => matches(f.name, search, spellings)) }))
    .filter((g) => g.files.length);
}
