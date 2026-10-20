import { describe, expect, it } from "bun:test";

import {
  dataAvailabilityTag,
  photometryTag,
  sourceTag,
  spectraTag,
} from "./cacheTags";

// [helper, tag type, how it stores a numeric id]
const perObjectTags = [
  [sourceTag, "Source", Number],
  [spectraTag, "Spectra", Number],
  [dataAvailabilityTag, "DataAvailability", Number],
  [photometryTag, "Photometry", String],
] as const;

for (const [tag, type, storedId] of perObjectTags) {
  describe(`${type} tag`, () => {
    it("scopes the tag to one object", () => {
      expect(tag("ZTF23abc")).toEqual([{ type, id: "ZTF23abc" }]);
    });

    it("keeps a numeric id, including 0", () => {
      expect(tag(42)).toEqual([{ type, id: storedId(42) }]);
      expect(tag(0)).toEqual([{ type, id: storedId(0) }]);
    });

    it("falls back to the broad tag when the id is missing", () => {
      expect(tag(undefined)).toEqual([{ type }]);
      expect(tag(null)).toEqual([{ type }]);
      expect(tag()).toEqual([{ type }]);
    });

    // An explicit `id: undefined` would make RTK treat the broad tag as a
    // distinct, never-matching tag.
    it("does not emit an id key for the broad tag", () => {
      expect("id" in tag(undefined)[0]).toBe(false);
    });

    it("does not match a different object", () => {
      expect(tag("ZTF23abc")).not.toEqual(tag("ZTF23xyz"));
    });
  });
}

describe("photometryTag", () => {
  // Providers key off the query arg and pushes off the payload; one may be a
  // number and the other a string for the same object.
  it("matches a numeric id and its string form", () => {
    expect(photometryTag("42")).toEqual(photometryTag(42));
  });
});

describe("spectraTag", () => {
  // The bulk query tags itself with every source it returned, so a refresh for
  // any one of them reaches it.
  it("builds one tag per source for a bulk result", () => {
    const sources = [{ id: "ZTF26abpgdyr" }, { id: "ZTF26aazzexf" }];
    expect(sources.flatMap((source) => spectraTag(source.id))).toEqual([
      { type: "Spectra", id: "ZTF26abpgdyr" },
      { type: "Spectra", id: "ZTF26aazzexf" },
    ]);
  });
});
