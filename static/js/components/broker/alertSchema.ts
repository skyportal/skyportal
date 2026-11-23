export interface SchemaField {
  path: string;
  type: string;
}

const PRIMITIVES = new Set([
  "null",
  "boolean",
  "int",
  "long",
  "float",
  "double",
  "bytes",
  "string",
]);

export const NAN_NOTE =
  "NaN when unset, so it is present and fails every comparison: pair a < cut with a > bound, or it also keeps the unset ones.";

const fieldNote = (field: any): string | null => {
  const docs = [field?.doc];
  const kind = field?.type;
  if (kind && typeof kind === "object" && !Array.isArray(kind)) {
    docs.push(kind.doc);
  }
  if (
    field?.nan_possible ||
    (kind && typeof kind === "object" && kind.nan_possible)
  ) {
    docs.push(NAN_NOTE);
  }
  const text = docs
    .filter((d) => typeof d === "string" && d.trim())
    .map((d) => d.trim())
    .join(" ");
  return text.split(/\s+/).join(" ") || null;
};

export const flattenSchema = (
  schema: any,
  prefix = "",
  registry: Record<string, any> = {},
  stack: string[] = [],
  depth = 0,
  notes: Record<string, string> = {},
): SchemaField[] => {
  if (depth > 12) return [];

  if (typeof schema === "string") {
    if (PRIMITIVES.has(schema) || stack.includes(schema) || !registry[schema]) {
      return prefix ? [{ path: prefix, type: schema }] : [];
    }
    return flattenSchema(
      registry[schema],
      prefix,
      registry,
      stack,
      depth,
      notes,
    );
  }

  if (Array.isArray(schema)) {
    const branches = schema.filter((b) => b !== "null");
    const nullable = branches.length < schema.length;
    if (branches.length === 0) {
      return prefix ? [{ path: prefix, type: "null" }] : [];
    }
    return flattenSchema(
      branches[0],
      prefix,
      registry,
      stack,
      depth,
      notes,
    ).map((f) =>
      nullable && f.path === prefix ? { ...f, type: `${f.type}?` } : f,
    );
  }

  if (!schema || typeof schema !== "object") return [];

  const kind = schema.type;
  if (schema.name && !registry[schema.name]) registry[schema.name] = schema;

  if (kind === "record") {
    const inner = [...stack, schema.name];
    return (schema.fields ?? []).flatMap((field: any) => {
      if (!field?.name) return [];
      const path = prefix ? `${prefix}.${field.name}` : field.name;
      const note = fieldNote(field);
      if (note) notes[path] = note;
      return flattenSchema(field.type, path, registry, inner, depth + 1, notes);
    });
  }
  if (kind === "array") {
    return flattenSchema(
      schema.items,
      `${prefix}[]`,
      registry,
      stack,
      depth + 1,
      notes,
    );
  }
  if (kind === "enum") {
    return [
      { path: prefix, type: `enum(${(schema.symbols ?? []).join("|")})` },
    ];
  }
  if (kind === "map") {
    return flattenSchema(
      schema.values,
      `${prefix}{}`,
      registry,
      stack,
      depth + 1,
      notes,
    );
  }
  return flattenSchema(kind, prefix, registry, stack, depth, notes);
};

export const noteOwner = (path: string, notes: Record<string, string>) => {
  const parts = path.split(".").map((part) => part.replace(/[[\]{}]+$/, ""));
  for (let stop = parts.length; stop > 0; stop -= 1) {
    const owner = parts.slice(0, stop).join(".");
    if (notes[owner]) return owner;
  }
  return null;
};
