// Per-object cache tags: `{ type, id }` refetches only that object's queries,
// and with no id the broad `{ type }` matches every query of the type (for
// mutations that do not know which object they changed).
const perObjectTag =
  <T extends string>(type: T) =>
  (id?: number | string | null): { type: T; id?: number | string }[] => [
    id != null ? { type, id } : { type },
  ];

export const sourceTag = perObjectTag("Source");
export const spectraTag = perObjectTag("Spectra");
export const dataAvailabilityTag = perObjectTag("DataAvailability");

const photometryObjectTag = perObjectTag("Photometry");

// Stringified: providers key off the query arg and pushes off the payload,
// which may differ in type for the same object.
export const photometryTag = (id?: number | string | null) =>
  photometryObjectTag(id != null ? String(id) : null);
