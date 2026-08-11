// Format an annotation value for display. Kept in a pure (React-free) module so
// it can be imported into unit tests without pulling in the component tree.
export const getAnnotationValueString = (value: any): string => {
  let valueString;
  const valueType = typeof value;
  switch (valueType) {
    case "number":
      // Keep integers (e.g. survey source ids) as integers; only round floats.
      valueString = Number.isInteger(value)
        ? value.toString()
        : value.toFixed(4);
      break;
    case "object":
      valueString = JSON.stringify(value, null, 2);
      break;
    default:
      valueString = value.toString();
  }
  return valueString;
};

// Some annotations nest their fields one level down -- the GCN crossmatch keys
// its measurements per event, so the whole set would otherwise render as a
// single unreadable JSON blob. Give every leaf its own row, named "event.field".
// Arrays stay whole: they are usually one value, not a group of them.
export const flattenAnnotationData = (
  data: Record<string, any>,
  maxDepth = 2,
): [string, any][] => {
  const rows: [string, any][] = [];
  const walk = (value: any, path: string, depth: number) => {
    const isPlainObject =
      value !== null && typeof value === "object" && !Array.isArray(value);
    if (isPlainObject && depth < maxDepth && Object.keys(value).length > 0) {
      Object.entries(value).forEach(([key, inner]) =>
        walk(inner, path ? `${path}.${key}` : key, depth + 1),
      );
      return;
    }
    rows.push([path, value]);
  };
  Object.entries(data || {}).forEach(([key, value]) => walk(value, key, 1));
  return rows;
};
