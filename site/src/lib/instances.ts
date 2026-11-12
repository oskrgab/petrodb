import type { InstanceGroup } from "./types.ts";

/**
 * The Instance browser's filter: keep one Event class ("all" keeps every one)
 * and the Instances whose `instance_id` contains `search`, ignoring case.
 * Groups left empty are dropped.
 */
export function filterInstances(groups: InstanceGroup[], eventClass: string, search: string): InstanceGroup[] {
  const needle = search.trim().toLowerCase();
  return groups
    .filter((g) => eventClass === "all" || String(g.eventClass) === eventClass)
    .map((g) => ({ ...g, files: g.files.filter((f) => f.instanceId.toLowerCase().includes(needle)) }))
    .filter((g) => g.files.length);
}
