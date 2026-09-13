import { describe, it, expect } from "bun:test";

import { getAnnotationValueString } from "./annotationValue";

describe("getAnnotationValueString", () => {
  it("keeps integers as integers (e.g. survey source ids)", () => {
    expect(getAnnotationValueString(12345)).toBe("12345");
    expect(getAnnotationValueString(-7)).toBe("-7");
    expect(getAnnotationValueString(0)).toBe("0");
  });

  it("rounds non-integer numbers to 4 decimals", () => {
    expect(getAnnotationValueString(1.23456789)).toBe("1.2346");
    expect(getAnnotationValueString(0.5)).toBe("0.5000");
  });

  it("passes strings through unchanged", () => {
    expect(getAnnotationValueString("ZTF21abc")).toBe("ZTF21abc");
  });

  it("JSON-stringifies objects", () => {
    expect(getAnnotationValueString({ a: 1 })).toBe(
      JSON.stringify({ a: 1 }, null, 2),
    );
  });
});
