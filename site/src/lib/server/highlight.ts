import { createHighlighter, createCssVariablesTheme } from "shiki";

// Colours come from CSS custom properties (--shiki-*), so code follows the
// page theme with no client-side work.
const theme = createCssVariablesTheme({ name: "petrodb", variablePrefix: "--shiki-" });

const highlighter = await createHighlighter({ themes: [theme], langs: ["sql", "python"] });

export function highlight(code: string, lang: "sql" | "python"): string {
  return highlighter.codeToHtml(code, { lang, theme: "petrodb" });
}
