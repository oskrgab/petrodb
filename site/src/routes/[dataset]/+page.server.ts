import { error } from "@sveltejs/kit";
import { DATASET_IDS, loadDataset, loadSummary, skipReason } from "$lib/server/datasets";

/**
 * Only Datasets that are ready get a page. A ready Dataset whose tree is built
 * in CI is skipped where that tree is absent, and the build says so.
 */
export function entries() {
  for (const id of DATASET_IDS) {
    const reason = skipReason(id);
    if (reason) console.log(`Skipped the /${id}/ page: ${reason}`);
  }
  return DATASET_IDS.filter((id) => loadSummary(id).ready).map((dataset) => ({ dataset }));
}

export function load({ params }) {
  if (!DATASET_IDS.includes(params.dataset)) error(404, "No such dataset");
  return loadDataset(params.dataset);
}
