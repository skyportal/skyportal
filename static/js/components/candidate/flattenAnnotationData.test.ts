import { describe, it, expect } from "bun:test";

import { flattenAnnotationData } from "./annotationValue";

describe("flattenAnnotationData", () => {
  it("gives each field of a per-event annotation its own row", () => {
    // The GCN crossmatch keys its measurements by event, so without flattening
    // the whole set renders as one unreadable JSON blob.
    const data = {
      sb26080812: { delta_t: -0.19, distance_arcmin: 3.22, drb: 1.0 },
    };
    expect(flattenAnnotationData(data)).toEqual([
      ["sb26080812.delta_t", -0.19],
      ["sb26080812.distance_arcmin", 3.22],
      ["sb26080812.drb", 1.0],
    ]);
  });

  it("leaves an already-flat annotation untouched", () => {
    expect(flattenAnnotationData({ age: 1, n_det: 5 })).toEqual([
      ["age", 1],
      ["n_det", 5],
    ]);
  });

  it("keeps arrays whole rather than splitting them into rows", () => {
    expect(flattenAnnotationData({ tags: ["a", "b"] })).toEqual([
      ["tags", ["a", "b"]],
    ]);
  });

  it("keeps an empty object as a value instead of dropping the row", () => {
    expect(flattenAnnotationData({ thing: {} })).toEqual([["thing", {}]]);
  });

  it("stops at the depth limit rather than recursing without bound", () => {
    expect(flattenAnnotationData({ a: { b: { c: 1 } } })).toEqual([
      ["a.b", { c: 1 }],
    ]);
  });

  it("tolerates null and undefined data", () => {
    expect(flattenAnnotationData(null as any)).toEqual([]);
    expect(flattenAnnotationData({ nothing: null })).toEqual([
      ["nothing", null],
    ]);
  });
});
