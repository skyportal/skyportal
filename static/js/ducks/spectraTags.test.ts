import { describe, expect, it } from "bun:test";

import { spectraTag } from "./spectraTags";

describe("spectraTag", () => {
  it("scopes the tag to one object", () => {
    expect(spectraTag("ZTF26abpgdyr")).toEqual([
      { type: "Spectra", id: "ZTF26abpgdyr" },
    ]);
  });

  it("falls back to the broad tag when the object is unknown", () => {
    expect(spectraTag()).toEqual([{ type: "Spectra" }]);
    expect(spectraTag(null)).toEqual([{ type: "Spectra" }]);
  });

  // A per-object tag must not match another object's cache entry: that is what
  // made every open source page refetch on any source's spectra changing.
  it("does not match a different object", () => {
    expect(spectraTag("ZTF26abpgdyr")).not.toEqual(spectraTag("ZTF26aazzexf"));
  });

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
