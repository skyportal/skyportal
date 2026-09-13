// Pure helpers for SourceTable annotation/altdata columns. Extracted so the
// correctness-critical parts (registry -> metadata, saved-field parsing, picker
// options) are unit-testable without rendering the grid.
//
// Only the user's *saved* fields become columns: the annotations registry is
// unbounded (per-object origins like `ls_dr9-<objid>`), so materializing a
// column per (origin, key) froze the grid. Discovery goes through the picker.

export interface AnnotationColumnInfo {
  origin: string;
  key: string;
}

export interface ColumnPickerOption {
  field: string;
  label: string;
}

// annotationsInfo: { origin: [{ key: type }, ...] }
//   -> { "annotation.<origin>.<key>": { origin, key } }
export function buildAnnotationColumnMeta(
  annotationsInfo: Record<string, any[]> | null | undefined,
): Record<string, AnnotationColumnInfo> {
  const meta: Record<string, AnnotationColumnInfo> = {};
  Object.entries(annotationsInfo || {}).forEach(([origin, keys]) => {
    (keys || []).forEach((keyObj) => {
      const key = Object.keys(keyObj || {})[0];
      if (key) {
        meta[`annotation.${origin}.${key}`] = { origin, key };
      }
    });
  });
  return meta;
}

// altdataInfo: { keys: [{ key: type }, ...] } -> { "altdata.<key>": { key } }
export function buildAltdataColumnMeta(
  altdataInfo: { keys?: any[] } | null | undefined,
): Record<string, { key: string }> {
  const meta: Record<string, { key: string }> = {};
  (altdataInfo?.keys || []).forEach((keyObj) => {
    const key = Object.keys(keyObj || {})[0];
    if (key) {
      meta[`altdata.${key}`] = { key };
    }
  });
  return meta;
}

// Resolve a saved "annotation.<origin>.<key>" field back to origin/key. Uses the
// registry when present, and a split fallback when the origin has aged out of it
// (origins carry no dots; keys are the last segment).
export function originKeyForAnnotationField(
  field: string,
  meta: Record<string, AnnotationColumnInfo>,
): AnnotationColumnInfo {
  const m = meta[field];
  if (m) {
    return m;
  }
  const parts = field.split(".");
  return {
    origin: parts.slice(1, -1).join("."),
    key: parts[parts.length - 1] ?? field,
  };
}

// Resolve a saved "altdata.<key>" field back to its key.
export function altdataKeyForField(
  field: string,
  meta: Record<string, { key: string }>,
): string {
  return meta[field]?.key ?? field.slice("altdata.".length);
}

// Every discoverable field as a picker option { field, label }.
export function buildColumnPickerOptions(
  annotationMeta: Record<string, AnnotationColumnInfo>,
  altdataMeta: Record<string, { key: string }>,
): ColumnPickerOption[] {
  return [
    ...Object.keys(annotationMeta).map((field) => {
      const m = annotationMeta[field];
      return { field, label: m ? `${m.key} (${m.origin})` : field };
    }),
    ...Object.keys(altdataMeta).map((field) => {
      const m = altdataMeta[field];
      return { field, label: m ? `${m.key} (altdata)` : field };
    }),
  ];
}

// Picker filter: nothing until the user types, then case-insensitive substring
// matches capped at `limit` so a large registry never floods the dropdown.
export function filterColumnPickerOptions(
  options: ColumnPickerOption[],
  query: string,
  limit = 50,
): ColumnPickerOption[] {
  const q = query.trim().toLowerCase();
  if (!q) {
    return [];
  }
  return options
    .filter((o) => o.label.toLowerCase().includes(q))
    .slice(0, limit);
}
