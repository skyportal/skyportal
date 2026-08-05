import embed from "vega-embed";

/**
 * Give Vega data objects it is allowed to extend.
 *
 * Vega tags every datum with a `Symbol("vega_id")`, which throws
 * (`Object is not extensible`) on the frozen objects RTK Query hands back, and
 * the plot silently renders an empty container. Specs are built locally by the
 * calling component, so the `values` arrays are replaced in place.
 */
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

/**
 * Embed a Vega spec, guarding the two things every call site here needs: React
 * passes `null` to a ref on unmount, and Vega must not be handed frozen data.
 */
const embedVega = (node: HTMLElement | null, spec: any, options: any = {}) => {
  if (!node) {
    return undefined;
  }
  cloneSpecValues(spec);
  return embed(node, spec, { actions: false, ...options });
};

export default embedVega;
