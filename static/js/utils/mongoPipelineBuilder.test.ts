import { describe, it, expect } from "bun:test";

import { buildMongoAggregationPipeline } from "./mongoPipelineBuilder.js";

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
