export function bytes(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)} MB`;
  return `${Math.max(1, Math.round(n / 1e3))} kB`;
}

export function count(n: number): string {
  return n.toLocaleString("en-US");
}

/** 17,775,911 → "17.8 million"; small numbers stay exact. */
export function approx(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)} million`;
  return count(n);
}
