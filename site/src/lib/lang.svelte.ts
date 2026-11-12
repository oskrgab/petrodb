import type { Snippet } from "./types";

/** The language a visitor last picked, shared by every snippet on the page. */
export const preferred = $state<{ lang: Snippet["lang"] }>({ lang: "sql" });
