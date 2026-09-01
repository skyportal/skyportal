/** The crossmatch annotation the per-event fields are read from.
 *
 * Lower case: the sources query compares against `lower(annotations.origin)`.
 */
export const CROSSMATCH_ORIGIN = "gcn-crossmatch";

/** Turn the form's annotation fields into the API's "name: value: operator"
 * triplets.
 *
 * These fields live one level down in the crossmatch annotation, keyed by
 * event, since one source can fall inside several localizations. The sources
 * query matches that level and scopes it to the event being viewed.
 */
export const buildAnnotationFilters = (
  formData: Record<string, any>,
): string[] => {
  const filters: string[] = [];
  const add = (name: string, value: any, op: string) => {
    if (value !== undefined && value !== null && value !== "") {
      filters.push(`${name}: ${value}: ${op}`);
    }
  };
  // A high PS1 star score means the source sits on a star.
  add("sgscore", formData["maxSgscore"], "lt");
  // Age is days from first detection: an old source is not a new counterpart.
  add("age", formData["maxAge"], "lt");
  add("ndethist", formData["minNdethist"], "ge");
  // delta_t is negative before the event, so a floor drops detections from
  // long before it.
  add("delta_t", formData["minDeltaT"], "ge");
  return filters;
};
