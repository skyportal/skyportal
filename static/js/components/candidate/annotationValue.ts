export const getAnnotationValueString = (value: any): string => {
  switch (typeof value) {
    case "number":
      return Number.isInteger(value) ? value.toString() : value.toFixed(4);
    case "object":
      return JSON.stringify(value, null, 2);
    default:
      return value.toString();
  }
};

export const flattenAnnotationData = (
  data: Record<string, any>,
  maxDepth = 2,
): [string, any][] => {
  const walk = (value: any, path: string, depth: number): [string, any][] =>
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    depth < maxDepth &&
    Object.keys(value).length > 0
      ? Object.entries(value).flatMap(([key, inner]) =>
          walk(inner, path ? `${path}.${key}` : key, depth + 1),
        )
      : [[path, value]];
  return Object.entries(data || {}).flatMap(([key, value]) =>
    walk(value, key, 1),
  );
};
