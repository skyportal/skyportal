// Per-object Spectra cache invalidation helper.
//
// The per-source spectra queries are tagged `{ type: "Spectra", id: objId }`, so
// a refresh for one source leaves every other open source page alone. The broad
// `{ type: "Spectra" }` fallback matches every spectra query, and is for the
// mutations keyed on a spectrum id, which do not know the object it belongs to.
// Invalidating the broad tag still matches the per-object entries.
export const spectraTag = (
  id?: number | string | null,
): { type: "Spectra"; id?: number | string }[] => [
  id != null ? { type: "Spectra", id } : { type: "Spectra" },
];
