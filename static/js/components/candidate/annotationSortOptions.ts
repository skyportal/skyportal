// Cap how many annotation-origin options a selector renders: origins can be
// unbounded, so an uncapped dropdown mounts thousands of items and hangs.
// Empty query -> the first `limit` (dropdown isn't blank on open); typing
// narrows via case-insensitive substring match, still capped.
export function filterAnnotationOrigins(
  origins: string[],
  query: string,
  limit = 50,
): string[] {
  const q = query.trim().toLowerCase();
  const matches = q
    ? origins.filter((o) => o.toLowerCase().includes(q))
    : origins;
  return matches.slice(0, limit);
}
