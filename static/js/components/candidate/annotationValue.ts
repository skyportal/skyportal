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
