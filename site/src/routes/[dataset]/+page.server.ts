import { error } from "@sveltejs/kit";
import { DATASET_IDS, loadDataset, loadSummary } from "$lib/server/datasets";

/** Only Datasets marked ready have a page; the rest are still on the old Landing. */
export function entries() {
  return DATASET_IDS.filter((id) => loadSummary(id).ready).map((dataset) => ({ dataset }));
}

export function load({ params }) {
  if (!DATASET_IDS.includes(params.dataset)) error(404, "No such dataset");
  return loadDataset(params.dataset);
}
