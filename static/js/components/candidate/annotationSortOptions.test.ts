import { describe, it, expect } from "bun:test";

import { filterAnnotationOrigins } from "./annotationSortOptions";

// Annotation origins can be unbounded (one per object), so the selector must cap
// what it renders or the dropdown hangs.
const origins = [
  ...Array.from({ length: 200 }, (_, i) => `ls_dr9-${i}`),
  "gaiadr3.gaia_source",
  "acai:high_h__high_n",
];

describe("filterAnnotationOrigins", () => {
  it("caps how many render when nothing is typed", () => {
    expect(filterAnnotationOrigins(origins, "", 50)).toHaveLength(50);
    // (default limit)
    expect(filterAnnotationOrigins(origins, "")).toHaveLength(50);
  });

  it("substring-matches case-insensitively", () => {
    expect(filterAnnotationOrigins(origins, "GAIA")).toEqual([
      "gaiadr3.gaia_source",
    ]);
    expect(filterAnnotationOrigins(origins, "acai")).toEqual([
      "acai:high_h__high_n",
    ]);
  });

  it("still caps a large match set", () => {
    expect(filterAnnotationOrigins(origins, "ls_dr9", 10)).toHaveLength(10);
  });

  it("returns every match when under the limit", () => {
    expect(filterAnnotationOrigins(["a_x", "b_y"], "x")).toEqual(["a_x"]);
  });
});
