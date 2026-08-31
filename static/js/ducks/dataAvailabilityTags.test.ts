import { describe, expect, it } from "bun:test";

import { dataAvailabilityTag } from "./dataAvailabilityTags";

describe("dataAvailabilityTag", () => {
  it("scopes the tag to one object", () => {
    expect(dataAvailabilityTag("ZTF26abpgdyr")).toEqual([
      { type: "DataAvailability", id: "ZTF26abpgdyr" },
    ]);
  });

  it("falls back to the broad tag when the object is unknown", () => {
    expect(dataAvailabilityTag()).toEqual([{ type: "DataAvailability" }]);
    expect(dataAvailabilityTag(null)).toEqual([{ type: "DataAvailability" }]);
  });

  // A per-object tag must not match another object's cache entry: that is what
  // made every open source page refetch on any source's REFRESH_SOURCE.
  it("does not match a different object", () => {
    expect(dataAvailabilityTag("ZTF26abpgdyr")).not.toEqual(
      dataAvailabilityTag("ZTF26aazzexf"),
    );
  });
});
