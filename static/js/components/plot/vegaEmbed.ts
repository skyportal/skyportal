import embed from "vega-embed";

// Vega tags each datum with a Symbol, which throws on the frozen objects RTK
// Query returns, so hand it copies. Specs are built by the caller, so the
// `values` arrays are replaced in place.
const cloneSpecValues = (node: any) => {
  if (Array.isArray(node)) {
    node.forEach(cloneSpecValues);
    return;
  }
  if (!node || typeof node !== "object") {
    return;
  }
  Object.entries(node).forEach(([key, value]) => {
    if (key === "values" && Array.isArray(value)) {
      node[key] = value.map((datum: any) =>
        datum && typeof datum === "object" ? { ...datum } : datum,
      );
    } else {
      cloneSpecValues(value);
    }
  });
};

// Also skips the null node React passes to a ref on unmount.
const embedVega = (node: HTMLElement | null, spec: any, options: any = {}) => {
  if (!node) {
    return undefined;
  }
  cloneSpecValues(spec);
  return embed(node, spec, { actions: false, ...options });
};

export default embedVega;
