export interface AlertFilter {
  field: string;
  op: string;
  value: string;
}

export const OPERATORS = ["=", "≠", "<", "≤", ">", "≥", "contains"];

// Dot-notation view of an alert, so nested provider fields are filterable and
// exportable as flat CSV columns.
export const flatten = (
  value: any,
  prefix = "",
  out: Record<string, any> = {},
) => {
  Object.entries(value ?? {}).forEach(([key, v]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (v && typeof v === "object" && !Array.isArray(v)) flatten(v, path, out);
    else out[path] = Array.isArray(v) ? JSON.stringify(v) : v;
  });
  return out;
};

export const fieldsOf = (rows: Record<string, any>[]) =>
  [...new Set(rows.flatMap((r) => Object.keys(r)))].sort();

const compare = (left: any, right: string, op: string) => {
  const a = Number(left);
  const b = Number(right);
  const numeric = !Number.isNaN(a) && !Number.isNaN(b) && right.trim() !== "";
  const text = String(left ?? "").toLowerCase();
  const target = right.toLowerCase();
  switch (op) {
    case "=":
      return numeric ? a === b : text === target;
    case "≠":
      return numeric ? a !== b : text !== target;
    case "<":
      return numeric && a < b;
    case "≤":
      return numeric && a <= b;
    case ">":
      return numeric && a > b;
    case "≥":
      return numeric && a >= b;
    default:
      return text.includes(target);
  }
};

export const matchesFilters = (
  flat: Record<string, any>,
  filters: AlertFilter[],
) =>
  filters.every(
    (f) => !f.field || !f.value || compare(flat[f.field], f.value, f.op),
  );

const escape = (v: any) => {
  if (v === null || v === undefined) return "";
  const s = typeof v === "object" ? JSON.stringify(v) : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export const toCsv = (rows: Record<string, any>[]) => {
  const fields = fieldsOf(rows);
  const body = rows.map((r) => fields.map((f) => escape(r[f])).join(","));
  return [fields.join(","), ...body].join("\n");
};

const download = (content: string, type: string, filename: string) => {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const downloadCsv = (rows: Record<string, any>[], filename: string) =>
  download(toCsv(rows), "text/csv;charset=utf-8;", filename);

// Raw records, not the flattened ones: JSON keeps the provider's nesting.
export const downloadJson = (rows: unknown[], filename: string) =>
  download(
    JSON.stringify(rows, null, 2),
    "application/json;charset=utf-8;",
    filename,
  );
