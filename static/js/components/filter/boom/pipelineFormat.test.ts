import { describe, it, expect } from "bun:test";

import { isRawMongoPipeline } from "./pipelineFormat";

describe("isRawMongoPipeline", () => {
  it("detects a raw Mongo pipeline imported via the broker API", () => {
    // Stages keyed entirely by $-operators: the block builder can't render these,
    // so they must be shown read-only instead of a blank canvas.
    const pipeline = [
      { $match: { "candidate.drb": { $gt: 0.5 } } },
      { $project: { objectId: 1, candidate: 1 } },
    ];
    expect(isRawMongoPipeline(pipeline)).toBe(true);
  });

  it("rejects block-builder filters so they still render as editable blocks", () => {
    const blocks = [
      {
        id: "root-block",
        category: "block",
        operator: "and",
        children: [],
      },
    ];
    expect(isRawMongoPipeline(blocks)).toBe(false);
  });

  it("rejects a stage that mixes $-operators with plain keys (e.g. a block)", () => {
    expect(isRawMongoPipeline([{ $match: {}, category: "block" }])).toBe(false);
  });

  it("rejects empty, non-array, and empty-stage inputs", () => {
    expect(isRawMongoPipeline([])).toBe(false);
    expect(isRawMongoPipeline(null)).toBe(false);
    expect(isRawMongoPipeline(undefined)).toBe(false);
    expect(isRawMongoPipeline([{}])).toBe(false);
    expect(isRawMongoPipeline([{ $match: {} }, null])).toBe(false);
  });
});
