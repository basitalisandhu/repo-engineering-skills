export function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export const slugify = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "-");
