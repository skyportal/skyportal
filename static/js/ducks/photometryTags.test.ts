import { describe, it, expect } from "bun:test";

import { photometryTag } from "./photometryTags";

// A photometry push carries one obj_id. Tagging per id is what stops it
// refetching the photometry another open page is showing, which resets that
// plot's zoom.
describe("photometryTag", () => {
  it("returns a per-id tag for an obj_id", () => {
    expect(photometryTag("ZTF23abc")).toEqual([
      { type: "Photometry", id: "ZTF23abc" },
    ]);
  });

  it("stringifies a numeric id so provider and invalidation match", () => {
    // Providers key off the query arg and pushes off the payload; one may be a
    // number and the other a string for the same object.
    expect(photometryTag(42)).toEqual([{ type: "Photometry", id: "42" }]);
    expect(photometryTag("42")).toEqual(photometryTag(42));
  });

  it("falls back to the broad tag when the id is missing", () => {
    expect(photometryTag(undefined)).toEqual([{ type: "Photometry" }]);
    expect(photometryTag(null)).toEqual([{ type: "Photometry" }]);
    expect(photometryTag()).toEqual([{ type: "Photometry" }]);
  });

  it("does not match a different object", () => {
    expect(photometryTag("ZTF23abc")).not.toEqual(photometryTag("ZTF23xyz"));
  });
});
