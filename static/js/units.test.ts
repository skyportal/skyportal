import { describe, expect, it } from "bun:test";

import { dec_to_deg, ra_to_deg } from "./units";

describe("ra_to_deg", () => {
  it("converts sexagesimal HH:MM:SS to decimal degrees", () => {
    // ZTF J200136.79+122900.5
    expect(ra_to_deg("20:01:36.795")).toBeCloseTo(300.40331, 4);
  });

  it("passes decimal degrees through", () => {
    expect(ra_to_deg("300.4")).toBe(300.4);
  });
});

describe("dec_to_deg", () => {
  it("converts sexagesimal ±DD:MM:SS to decimal degrees", () => {
    expect(dec_to_deg("+12:29:00.485")).toBeCloseTo(12.48347, 4);
  });

  it("handles negative declinations", () => {
    expect(dec_to_deg("-12:29:00.485")).toBeCloseTo(-12.48347, 4);
  });

  it("passes decimal degrees through", () => {
    expect(dec_to_deg("-12.5")).toBe(-12.5);
  });
});
