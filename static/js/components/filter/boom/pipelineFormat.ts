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

// Field paths a $match reads, e.g. "candidate.drb" in {"candidate.drb": {"$gt": 0.9}}.
const matchedFields = (match: any, fields = new Set<string>()): Set<string> => {
  if (Array.isArray(match)) match.forEach((m) => matchedFields(m, fields));
  else if (match && typeof match === "object") {
    Object.entries(match).forEach(([key, value]) => {
      if (!key.startsWith("$")) fields.add(key);
      matchedFields(value, fields);
    });
  }
  return fields;
};

// True when a $project only keeps what the block builder projects by itself
// (objectId, candidate.jd and the fields its conditions use), so dropping it
// loses nothing when the pipeline is turned into blocks.
export const isBuilderProjection = (project: any, match: any): boolean => {
  if (!project || typeof project !== "object" || Array.isArray(project))
    return false;
  const used = matchedFields(match);
  return Object.entries(project).every(
    ([field, value]) =>
      value === 1 &&
      (field === "objectId" ||
        field === "candidate.jd" ||
        [...used].some((u) => u === field || u.startsWith(`${field}.`))),
  );
};
