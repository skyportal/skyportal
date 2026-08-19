import { describe, expect, it } from "bun:test";

import { decToDeg, raToDeg } from "./coneCoords";

describe("raToDeg", () => {
  it("converts sexagesimal HH:MM:SS to decimal degrees", () => {
    // ZTF J200136.79+122900.5
    expect(raToDeg("20:01:36.795")).toBeCloseTo(300.40331, 4);
  });

  it("passes decimal degrees through", () => {
    expect(raToDeg("300.4")).toBe(300.4);
  });
});

describe("decToDeg", () => {
  it("converts sexagesimal ±DD:MM:SS to decimal degrees", () => {
    expect(decToDeg("+12:29:00.485")).toBeCloseTo(12.48347, 4);
  });

  it("handles negative declinations", () => {
    expect(decToDeg("-12:29:00.485")).toBeCloseTo(-12.48347, 4);
  });

  it("passes decimal degrees through", () => {
    expect(decToDeg("-12.5")).toBe(-12.5);
  });
});
