import { describe, expect, it } from "bun:test";

import { compileFilterPipeline } from "./compileFilterPipeline.js";
import { convertToMongoAggregation } from "./mongoPipelineBuilder.js";
import {
  decompileFilterPipeline,
  decompilePipeline,
} from "./mongoPipelineDecompiler.js";
import { sameBehavior } from "./pipelineSemantics.js";

const match = (m: any) => [{ $match: m }];

const FIELD_OPTIONS = [
  "candidate.jd",
  "candidate.jdstarthist",
  "candidate.magpsf",
  "candidate.drb",
  "prv_candidates",
  "prv_candidates.jd",
].map((label) => ({ label, type: "number" }));

const recompile = (pipeline: any) =>
  convertToMongoAggregation(decompilePipeline(pipeline));

const nodes = (tree: any[]): any[] =>
  tree.flatMap((node: any) => [node, ...nodes(node.children ?? [])]);

const fieldName = (condition: any) => condition.field?.name ?? condition.field;

describe("shapes it can represent", () => {
  it("reads a single comparison", () => {
    const tree: any = decompilePipeline(
      match({ "candidate.drb": { $gt: 0.9 } }),
    );
    expect(tree[0].category).toBe("block");
    expect(fieldName(tree[0].children[0])).toBe("candidate.drb");
    expect(tree[0].children[0]).toMatchObject({ operator: "$gt", value: 0.9 });
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

  it("reads a negation as an inverted block", () => {
    const tree: any = decompilePipeline(match({ a: { $not: { $gt: 1 } } }));
    expect(tree[0].children[0]).toMatchObject({ isTrue: false });
  });

  it("reads two operators on one field as two conditions", () => {
    const tree: any = decompilePipeline(match({ a: { $gt: 1, $lt: 5 } }));
    expect(tree[0].children).toHaveLength(2);
  });
});

describe("shapes it refuses", () => {
  it.each([
    ["a pipeline that drops objectId", [{ $project: { a: 1 } }]],
    ["an element match", match({ a: { $elemMatch: { b: 1 } } })],
    ["an empty disjunction", match({ $or: [] })],
    ["something that is not a pipeline", { $match: {} }],
    ["nothing", null],
  ])("refuses %s", (_label, pipeline) => {
    expect(decompilePipeline(pipeline as any)).toBeNull();
  });

  it("names what blocks cannot express", () => {
    const result = decompileFilterPipeline([
      {
        $project: {
          objectId: 1,
          pairs: { $zip: { inputs: ["$a", "$b"] } },
        },
      },
      { $match: { "pairs.0": { $exists: true } } },
    ]);
    expect(result.error).toContain("$zip");
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
    expect(recompile(match({ a: { $gt: 1 }, b: { $lt: 2 } }))).toEqual(
      match({ $and: [{ a: { $gt: 1 } }, { b: { $lt: 2 } }] }),
    );
    expect(recompile(match({ a: true }))).toEqual(match({ a: { $eq: true } }));
  });

  it("gives the builder a tree it can edit", () => {
    const tree: any = decompilePipeline(
      match({ a: { $gt: 1 }, b: { $lt: 2 } }),
    );
    for (const node of nodes(tree)) {
      expect(node.id).toBeTruthy();
      expect(["block", "condition"]).toContain(node.category);
    }
  });
});

const KOWALSKI_STYLE = [
  {
    $project: {
      objectId: 1,
      prv_candidates: 1,
      t_now: "$candidate.jd",
      m_now: "$candidate.magpsf",
      drb: "$candidate.drb",
      age: { $subtract: ["$candidate.jd", "$candidate.jdstarthist"] },
    },
  },
  {
    $project: {
      objectId: 1,
      t_now: 1,
      m_now: 1,
      age: 1,
      real: { $and: [{ $gt: ["$drb", 0.5] }, { $lt: ["$age", 30] }] },
      stationary: {
        $anyElementTrue: {
          $map: {
            input: "$prv_candidates",
            as: "cand",
            in: {
              $gt: [{ $abs: { $subtract: ["$t_now", "$$cand.jd"] } }, 0.02],
            },
          },
        },
      },
    },
  },
  { $match: { real: true, stationary: true } },
  {
    $project: {
      objectId: 1,
      "annotations.age": { $round: ["$age", 2] },
      "annotations.mag": "$m_now",
    },
  },
];

describe("converting a hand-written pipeline", () => {
  const result: any = decompileFilterPipeline(KOWALSKI_STYLE, {
    fieldOptions: FIELD_OPTIONS,
    streams: ["ZTF"],
  });

  it("converts it", () => {
    expect(result.error).toBeUndefined();
    expect(sameBehavior(KOWALSKI_STYLE, result.pipeline)).toBe(true);
  });

  it("matches the computed flags as conditions on variables", () => {
    const fields = nodes(result.filters)
      .filter((n: any) => n.category === "condition")
      .map(fieldName);
    expect(fields.sort()).toEqual(["real", "stationary"]);
  });

  it("keeps aggregation semantics for the flags", () => {
    const [real] = result.newVariables.switchCases;
    expect(real.name).toBe("real");
    expect(real.switchCondition.value.default).toBe(false);
  });

  it("turns the list scan into a list variable", () => {
    const [stationary] = result.newVariables.listVariables;
    expect(stationary.listCondition).toMatchObject({
      field: "prv_candidates",
      operator: "$anyElementTrue",
    });
  });

  it("turns the projection into annotations", () => {
    expect(
      result.projectionFields.map((p: any) => [p.outputName, p.type]),
    ).toEqual([
      ["age", "round"],
      ["mag", "include"],
    ]);
  });

  it("offers new variables to the filter's stream", () => {
    const all = Object.values(result.newVariables).flat() as any[];
    expect(all.every((v) => v.streams.includes("ZTF"))).toBe(true);
  });
});

describe("the shared variables", () => {
  const age = {
    name: "age",
    variable: "age = candidate.jd - candidate.jdstarthist",
    type: "number",
  };
  const pipeline = match({
    $expr: {
      $lt: [{ $subtract: ["$candidate.jd", "$candidate.jdstarthist"] }, 30],
    },
  });

  it("reuses one that computes the same thing", () => {
    const result: any = decompileFilterPipeline(pipeline, {
      fieldOptions: FIELD_OPTIONS,
      customVariables: [age],
    });
    expect(result.newVariables.variables).toEqual([]);
    expect(fieldName(result.filters[0].children[0])).toBe("age");
  });

  it("never takes the name of one that computes something else", () => {
    const other = { ...age, variable: "age = candidate.jd - 2460000" };
    const result: any = decompileFilterPipeline(
      match({
        $expr: {
          $lt: [{ $subtract: ["$candidate.jd", "$candidate.jdstarthist"] }, 30],
        },
        "candidate.drb": { $gt: 0.5 },
      }),
      { fieldOptions: FIELD_OPTIONS, customVariables: [other] },
    );
    const names = result.newVariables.variables.map((v: any) => v.name);
    expect(names).not.toContain("age");
  });
});

describe("a pipeline the builder wrote", () => {
  const listVariables = [
    {
      name: "hosted",
      listCondition: {
        type: "array",
        field: "cross_matches.NED",
        operator: "$anyElementTrue",
        value: {
          category: "block",
          logic: "And",
          children: [
            {
              category: "condition",
              field: "cross_matches.NED.distance_arcsec",
              operator: "$lt",
              value: "10",
            },
          ],
        },
      },
    },
  ];
  const pipeline = compileFilterPipeline({
    filters: [
      {
        category: "block",
        logic: "And",
        children: [
          {
            category: "condition",
            field: "candidate.drb",
            operator: "$gt",
            value: "0.8",
          },
          {
            category: "condition",
            field: "hosted",
            operator: "$eq",
            value: "true",
          },
        ],
      },
    ],
    projectionFields: [
      {
        fieldName: "candidate.magpsf",
        outputName: "mag",
        type: "round",
        roundDecimals: 0,
      },
    ],
    schema: {},
    fieldOptions: [],
    customVariables: [],
    customListVariables: listVariables,
    customSwitchCases: [],
  });

  it("comes back with the same variables and no new ones", () => {
    const result: any = decompileFilterPipeline(pipeline, {
      customListVariables: listVariables,
    });
    expect(result.error).toBeUndefined();
    expect(Object.values(result.newVariables).flat()).toEqual([]);
    expect(sameBehavior(pipeline, result.pipeline)).toBe(true);
  });

  it("keeps a rounding to zero decimals", () => {
    expect(pipeline[pipeline.length - 1].$project.annotations.mag).toEqual({
      $round: ["$candidate.magpsf", 0],
    });
  });
});
