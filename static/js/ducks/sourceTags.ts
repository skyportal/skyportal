// Per-id Source cache invalidation helper, shared by the source mutations.
//
// The per-source queries (getSource / getObjGroups / getSourcePosition /
// getAssociatedGcns) are tagged `{ type: "Source", id }`. A mutation scoped to
// one source invalidates `{ type: "Source", id }` so only that source's cache
// entries refetch, instead of every "Source"-tagged query across all sources.
// When the id is unknown (a delete keyed on a classification/assignment id, or
// a bulk op), we fall back to the broad `{ type: "Source" }` tag, which matches
// every source query — preserving the previous refresh-all behavior.
export const sourceTag = (
  id?: number | string | null,
): { type: "Source"; id?: number | string }[] => [
  id != null ? { type: "Source", id } : { type: "Source" },
];
