import { describe, it, expect } from "bun:test";

import {
  buildMongoAggregationPipeline,
  convertArithmeticExpression,
} from "./mongoPipelineBuilder.js";

const SUB_FIELD_OPTIONS = [
  { label: "cross_matches.NED.distance_kpc", type: "number" },
  { label: "cross_matches.NED.distance_arcsec", type: "number" },
];

const condition = (field: string, operator: string, value: string) => ({
  category: "condition",
  field,
  operator,
  value,
});

const listVariable = (operator: string, value: any) => ({
  name: "ned_host",
  listCondition: {
    operator,
    field: "cross_matches.NED",
    subFieldOptions: SUB_FIELD_OPTIONS,
    value,
  },
});

const FILTERS = [
  {
    category: "block",
    logic: "and",
    children: [
      {
        category: "condition",
        field: "ned_host",
        operator: "$eq",
        value: "true",
        isListVariable: true,
      },
    ],
  },
];

const listExpression = (listVar: any) => {
  const pipeline = buildMongoAggregationPipeline(
    FILTERS,
    {},
    [],
    [],
    [listVar],
    [],
  );
  const stage = pipeline.find((s: any) => s.$addFields?.ned_host);
  return stage.$addFields.ned_host;
};

describe("buildMongoAggregationPipeline list conditions", () => {
  it("keeps the or/and operator of the root block", () => {
    const expression = listExpression(
      listVariable("$anyElementTrue", {
        logic: "or",
        children: [
          {
            category: "block",
            logic: "and",
            children: [
              condition("cross_matches.NED.distance_kpc", "$eq", "-1"),
              condition("cross_matches.NED.distance_arcsec", "$lt", "300"),
            ],
          },
          {
            category: "block",
            logic: "and",
            children: [
              condition("cross_matches.NED.distance_kpc", "$gte", "0"),
              condition("cross_matches.NED.distance_kpc", "$lt", "30"),
            ],
          },
        ],
      }),
    );

    expect(expression.$anyElementTrue.$map.in.$or).toBeDefined();
  });

  it("keeps numeric values numeric on array subfields", () => {
    const expression = listExpression(
      listVariable("$anyElementTrue", {
        logic: "and",
        children: [condition("cross_matches.NED.distance_kpc", "$eq", "-1")],
      }),
    );

    expect(expression.$anyElementTrue.$map.in).toEqual({
      $eq: ["$$this.distance_kpc", -1],
    });
  });

  it("compiles an all-elements-true condition", () => {
    const expression = listExpression(
      listVariable("$allElementsTrue", {
        logic: "and",
        children: [condition("cross_matches.NED.distance_kpc", "$lt", "30")],
      }),
    );

    expect(expression.$allElementsTrue.$map.in).toEqual({
      $lt: ["$$this.distance_kpc", 30],
    });
  });
});

describe("buildMongoAggregationPipeline literal values", () => {
  it("reads a decimal comma as a number", () => {
    const pipeline = buildMongoAggregationPipeline([
      {
        category: "block",
        logic: "and",
        children: [condition("candidate.reliability", "$gt", "0,7")],
      },
    ]);

    expect(JSON.stringify(pipeline)).toContain(
      '"candidate.reliability":{"$gt":0.7}',
    );
  });
});

describe("convertArithmeticExpression", () => {
  it("associates subtraction and division to the left", () => {
    expect(convertArithmeticExpression("x = 0 - a - 3*b")).toEqual({
      $subtract: [{ $subtract: [0, "$a"] }, { $multiply: [3, "$b"] }],
    });
    expect(convertArithmeticExpression("x = a - b + c")).toEqual({
      $add: [{ $subtract: ["$a", "$b"] }, "$c"],
    });
    expect(convertArithmeticExpression("x = a / b / c")).toEqual({
      $divide: [{ $divide: ["$a", "$b"] }, "$c"],
    });
  });

  it("keeps powers right-associative and unary minus attached", () => {
    expect(convertArithmeticExpression("x = a^b^c")).toEqual({
      $pow: ["$a", { $pow: ["$b", "$c"] }],
    });
    expect(convertArithmeticExpression("x = a - -2")).toEqual({
      $subtract: ["$a", -2],
    });
  });
});

const root = (children: any[]) => [
  { category: "block", logic: "And", children },
];

const switchCase = (name: string, block: any, then: any, fallback?: any) => ({
  name,
  switchCondition: {
    operator: "$switch",
    value: { cases: [{ block, then }], default: fallback },
  },
});

const switchExpression = (pipeline: any[], name: string) =>
  pipeline.find((s: any) => s.$addFields?.[name]).$addFields[name];

describe("buildMongoAggregationPipeline expressions", () => {
  it("negates a block inside a switch case with $not", () => {
    const flag = switchCase(
      "not_bright",
      {
        category: "block",
        logic: "And",
        isTrue: false,
        children: [condition("candidate.magpsf", "$lt", "15")],
      },
      true,
      false,
    );
    const pipeline = buildMongoAggregationPipeline(
      root([condition("not_bright", "$eq", "true")]),
      {},
      [],
      [],
      [],
      [flag],
    );
    expect(switchExpression(pipeline, "not_bright").$switch.branches).toEqual([
      { case: { $not: [{ $lt: ["$candidate.magpsf", 15] }] }, then: true },
    ]);
  });

  it("keeps a switch branch whose value is false or zero", () => {
    const flag = switchCase(
      "faint",
      root([condition("candidate.magpsf", "$gt", "20")])[0],
      0,
      1,
    );
    const pipeline = buildMongoAggregationPipeline(
      root([condition("faint", "$eq", "1")]),
      {},
      [],
      [],
      [],
      [flag],
    );
    expect(switchExpression(pipeline, "faint").$switch.branches).toHaveLength(
      1,
    );
  });

  it("compares a list variable inside a switch case as an expression", () => {
    const hosted = {
      name: "hosted",
      listCondition: {
        operator: "$anyElementTrue",
        field: "cross_matches.NED",
      },
    };
    const flag = switchCase(
      "hosted_flag",
      root([condition("hosted", "$eq", "true")])[0],
      true,
      false,
    );
    const pipeline = buildMongoAggregationPipeline(
      root([condition("hosted_flag", "$eq", "true")]),
      {},
      [],
      [],
      [hosted],
      [flag],
    );
    expect(switchExpression(pipeline, "hosted_flag").$switch.branches).toEqual([
      { case: { $eq: ["$hosted", true] }, then: true },
    ]);
  });

  it("projects a whole field rather than only the parts a condition reads", () => {
    const fieldOptions = [
      { label: "prv_candidates", type: "array" },
      { label: "prv_candidates.magpsf", type: "number" },
    ];
    const recent = {
      name: "recent",
      listCondition: { operator: "$anyElementTrue", field: "prv_candidates" },
    };
    const pipeline = buildMongoAggregationPipeline(
      root([
        condition("prv_candidates.magpsf", "$lt", "20"),
        condition("recent", "$eq", "true"),
      ]),
      {},
      fieldOptions,
      [],
      [recent],
      [],
    );
    const initial = pipeline.find((s: any) => s.$project).$project;
    expect(initial.prv_candidates).toBe(1);
    expect(initial["prv_candidates.magpsf"]).toBeUndefined();
  });
});
