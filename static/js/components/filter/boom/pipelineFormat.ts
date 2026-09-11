// A block-builder filter is a tree of typed blocks (each has category === "block");
// a raw MongoDB aggregation pipeline is a list of stages keyed by $-operators (e.g.
// filters imported via the broker API). The block builder can't render the latter,
// so we detect it and show it read-only instead of a blank canvas.
export const isRawMongoPipeline = (data: any): boolean =>
  Array.isArray(data) &&
  data.length > 0 &&
  data.every(
    (stage: any) =>
      stage &&
      typeof stage === "object" &&
      !Array.isArray(stage) &&
      Object.keys(stage).length > 0 &&
      Object.keys(stage).every((k) => k.startsWith("$")),
  );
