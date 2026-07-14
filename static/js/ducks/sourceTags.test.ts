import { describe, it, expect } from "bun:test";

import { sourceTag } from "./sourceTags";

// The per-id vs broad contract is what keeps a single-source mutation from
// invalidating every "Source"-tagged query. Lock it in.
describe("sourceTag", () => {
  it("returns a per-id tag for a numeric id", () => {
    expect(sourceTag(42)).toEqual([{ type: "Source", id: 42 }]);
  });

  it("returns a per-id tag for a string obj_id", () => {
    expect(sourceTag("ZTF23abc")).toEqual([{ type: "Source", id: "ZTF23abc" }]);
  });

  it("falls back to the broad tag when the id is missing", () => {
    // undefined / null => broad { type: "Source" }, which RTK matches against
    // every source query (the previous refresh-all behavior).
    expect(sourceTag(undefined)).toEqual([{ type: "Source" }]);
    expect(sourceTag(null)).toEqual([{ type: "Source" }]);
    expect(sourceTag()).toEqual([{ type: "Source" }]);
  });

  it("treats id 0 as a real id (not missing)", () => {
    expect(sourceTag(0)).toEqual([{ type: "Source", id: 0 }]);
  });

  it("does not emit an undefined id key for the broad tag", () => {
    // A broad tag must be exactly { type: "Source" } — an explicit id:undefined
    // would make RTK treat it as a distinct (never-matching) tag.
    expect("id" in sourceTag(undefined)[0]).toBe(false);
  });
});
