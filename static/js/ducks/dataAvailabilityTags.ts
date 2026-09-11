// Per-object DataAvailability cache invalidation helper.
//
// getDataAvailability is tagged `{ type: "DataAvailability", id }` so a refresh
// for one source leaves every other open source page alone. The broad
// `{ type: "DataAvailability" }` fallback matches every availability query, and
// is for the mutations that answer a request without knowing which object it
// was about.
export const dataAvailabilityTag = (
  id?: string | null,
): { type: "DataAvailability"; id?: string }[] => [
  id != null ? { type: "DataAvailability", id } : { type: "DataAvailability" },
];
