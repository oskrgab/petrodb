import { DATASET_IDS, loadGlances, loadSummary } from "$lib/server/datasets";

export function load() {
  return {
    datasets: DATASET_IDS.map(loadSummary),
    // The home page opens on the simplest real query there is: one file, one GROUP BY.
    opener: loadGlances("volve")[0],
  };
}
