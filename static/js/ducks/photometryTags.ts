// Per-id Photometry cache invalidation helper, shared by the photometry queries
// and the websocket push.
//
// The per-source photometry queries are tagged `{ type: "Photometry", id }`, so
// a push about one object refetches only that object's photometry instead of
// every "Photometry"-tagged query. When the id is unknown we fall back to the
// broad `{ type: "Photometry" }` tag, which matches every photometry query.
export const photometryTag = (
  id?: number | string | null,
): { type: "Photometry"; id?: string }[] => [
  id != null ? { type: "Photometry", id: String(id) } : { type: "Photometry" },
];
