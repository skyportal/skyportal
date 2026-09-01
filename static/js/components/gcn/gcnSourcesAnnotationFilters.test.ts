import { describe, expect, it } from "bun:test";

import {
  CROSSMATCH_ORIGIN,
  buildAnnotationFilters,
} from "./gcnSourcesAnnotationFilters";

describe("buildAnnotationFilters", () => {
  it("is empty when nothing is set, so the query is unfiltered", () => {
    expect(buildAnnotationFilters({})).toEqual([]);
  });

  it("builds the API's name: value: operator triplets", () => {
    expect(buildAnnotationFilters({ maxSgscore: 0.7 })).toEqual([
      "sgscore: 0.7: lt",
    ]);
  });

  it("floors delta_t rather than capping it", () => {
    // delta_t is negative before the event, so a floor is what drops a
    // detection from long beforehand.
    expect(buildAnnotationFilters({ minDeltaT: -10 })).toEqual([
      "delta_t: -10: ge",
    ]);
  });

  it("combines every field that is set", () => {
    expect(
      buildAnnotationFilters({
        maxSgscore: 0.7,
        maxAge: 30,
        minNdethist: 2,
        minDeltaT: -10,
      }),
    ).toEqual([
      "sgscore: 0.7: lt",
      "age: 30: lt",
      "ndethist: 2: ge",
      "delta_t: -10: ge",
    ]);
  });

  it("keeps a zero, which is a real threshold", () => {
    expect(buildAnnotationFilters({ maxSgscore: 0 })).toEqual([
      "sgscore: 0: lt",
    ]);
  });

  it("names the origin the crossmatch fields live under", () => {
    expect(CROSSMATCH_ORIGIN).toBe("gcn-crossmatch");
  });
});
