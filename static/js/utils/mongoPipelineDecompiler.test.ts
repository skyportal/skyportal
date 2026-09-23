import { describe, expect, it } from "bun:test";

import { convertToMongoAggregation } from "./mongoPipelineBuilder.js";
import { decompilePipeline } from "./mongoPipelineDecompiler.js";

const match = (m: any) => [{ $match: m }];

// What the builder would run if the user saved the tree unchanged.
const recompile = (pipeline: any) =>
  convertToMongoAggregation(decompilePipeline(pipeline));

describe("shapes it can represent", () => {
  it("reads a single comparison", () => {
    const tree: any = decompilePipeline(
      match({ "candidate.drb": { $gt: 0.9 } }),
    );
    expect(tree[0].category).toBe("block");
    expect(tree[0].children[0]).toMatchObject({
      field: "candidate.drb",
      operator: "$gt",
      value: 0.9,
    });
  });

  it("reads several keys as a conjunction", () => {
    const tree: any = decompilePipeline(
      match({
        "candidate.drb": { $gt: 0.9 },
        "candidate.ndethist": { $gte: 2 },
      }),
    );
    expect(tree[0].logic).toBe("And");
    expect(tree[0].children).toHaveLength(2);
  });

  it("reads a nested disjunction", () => {
    const tree: any = decompilePipeline(
      match({
        $and: [
          { "candidate.drb": { $gt: 0.9 } },
          { $or: [{ a: { $lt: 1 } }, { b: { $lt: 0 } }] },
        ],
      }),
    );
    const nested = tree[0].children.find((c: any) => c.category === "block");
    expect(nested.logic).toBe("Or");
    expect(nested.children).toHaveLength(2);
  });

  it("reads a bare value as an equality test", () => {
    const tree: any = decompilePipeline(
      match({ "properties.stationary": true }),
    );
    expect(tree[0].children[0]).toMatchObject({ operator: "$eq", value: true });
  });

  it("reads existence and membership", () => {
    expect(
      decompilePipeline(match({ "properties.sso": { $exists: false } })),
    ).not.toBeNull();
    expect(
      decompilePipeline(match({ "candidate.band": { $in: ["g", "r"] } })),
    ).not.toBeNull();
  });
});

describe("shapes it refuses", () => {
  // Refusing is always safe: the caller keeps the pipeline read-only, which is
  // what it does with every pipeline today.
  it.each([
    [
      "more than one stage",
      [{ $match: { a: { $gt: 1 } } }, { $project: { a: 1 } }],
    ],
    ["a stage that is not $match", [{ $project: { a: 1 } }]],
    ["an aggregation expression", match({ $expr: { $gt: ["$a", "$b"] } })],
    ["an element match", match({ a: { $elemMatch: { b: 1 } } })],
    ["a negation", match({ a: { $not: { $gt: 1 } } })],
    ["two operators on one field", match({ a: { $gt: 1, $lt: 5 } })],
    ["an empty match", match({})],
    ["an empty disjunction", match({ $or: [] })],
    ["something that is not a pipeline", { $match: {} }],
    ["nothing", null],
  ])("refuses %s", (_label, pipeline) => {
    expect(decompilePipeline(pipeline as any)).toBeNull();
  });
});

describe("the round trip is what makes it safe", () => {
  it("returns a tree that compiles back to the same filter", () => {
    const pipeline = match({
      $and: [
        { "candidate.drb": { $gt: 0.9 } },
        {
          $or: [
            { "candidate.sgscore1": { $lt: 0.3 } },
            { "candidate.distpsnr1": { $lt: 0 } },
          ],
        },
      ],
    });
    expect(recompile(pipeline)).toEqual(pipeline);
  });

  it("normalises only in ways Mongo treats as identical", () => {
    // Several keys are an implicit conjunction and a bare value is an equality
    // test; the compiler spells both out, and nothing else may change.
    expect(recompile(match({ a: { $gt: 1 }, b: { $lt: 2 } }))).toEqual(
      match({ $and: [{ a: { $gt: 1 } }, { b: { $lt: 2 } }] }),
    );
    expect(recompile(match({ a: true }))).toEqual(match({ a: { $eq: true } }));
  });

  it("gives the builder a tree it can edit", () => {
    // Every node needs an id and a category, or the block components cannot
    // render or address it.
    const tree: any = decompilePipeline(
      match({ a: { $gt: 1 }, b: { $lt: 2 } }),
    );
    const walk = (node: any): any[] => [
      node,
      ...(node.children ?? []).flatMap(walk),
    ];
    for (const node of tree.flatMap(walk)) {
      expect(node.id).toBeTruthy();
      expect(["block", "condition"]).toContain(node.category);
    }
  });
});
