/**
 * Umami custom events. The tracker is the tag in `src/app.html`, which counts
 * the production hostnames only, so a caller needn't check where the page is.
 * Page views are the tracker's own; an event's data is all this adds, and it
 * names only what the Landing already publishes.
 */

/** What an event carries: Umami stores strings and numbers. */
export type EventData = Readonly<Record<string, string | number>>;

/** The part of `window` an event needs, so a test can stand in for it. */
export interface AnalyticsWindow {
  /** Defined by the tracker when it runs; absent until then, or for good if it's blocked. */
  readonly umami?: { track(name: string, data?: EventData): unknown };
  readonly document: { readonly readyState: DocumentReadyState };
  addEventListener(type: "load", listener: () => void, options: { once: true }): void;
}

/**
 * Send event `name` with `data`. The tracker is a deferred script, so an
 * event ready before it runs waits for the page's load event. A page that
 * loaded without it (an ad blocker, a failed fetch, a build with no website
 * id) drops the event.
 */
export function track(
  name: string,
  data: EventData,
  win: AnalyticsWindow = window as unknown as AnalyticsWindow,
): void {
  if (win.umami) {
    win.umami.track(name, data);
  } else if (win.document.readyState !== "complete") {
    win.addEventListener("load", () => win.umami?.track(name, data), { once: true });
  }
}

/** Data files and schema documents: a click on one is a use of the data, not a page view. */
const FILE = /\.(parquet|json|sql|md|ducklake)$/i;

/**
 * The event a followed link is worth, if any. A link to a file is `open-file`
 * with the file's path inside the published tree, whichever host and Hugging
 * Face revision serves it; any other link off the Landing is `outbound`. A
 * link to another Landing page is nothing: the tracker counts the page view.
 */
export function linkEvent(href: string, origin: string): { name: string; data: EventData } | null {
  let url: URL;
  try {
    url = new URL(href, origin);
  } catch {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null;
  if (FILE.test(url.pathname)) {
    return { name: "open-file", data: { file: url.pathname.replace(/^.*\/resolve\/[^/]+\//, "").replace(/^\//, "") } };
  }
  if (url.origin !== origin) {
    return { name: "outbound", data: { to: url.host + url.pathname.replace(/\/$/, "") } };
  }
  return null;
}
