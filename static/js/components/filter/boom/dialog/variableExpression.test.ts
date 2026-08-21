import { describe, expect, it } from "bun:test";

import { parseVariableExpression } from "./variableExpression";

describe("parseVariableExpression", () => {
  it("returns the expression after the '=' ", () => {
    expect(parseVariableExpression("significance = rate / rate_error")).toBe(
      "rate / rate_error",
    );
  });

  it("trims surrounding whitespace", () => {
    expect(parseVariableExpression("x=a+b")).toBe("a+b");
    expect(parseVariableExpression("  y  =  c * d  ")).toBe("c * d");
  });

  it("returns the whole string when there is no '='", () => {
    expect(parseVariableExpression("rate")).toBe("rate");
  });

  it("handles empty / missing input", () => {
    expect(parseVariableExpression("")).toBe("");
    // @ts-expect-error exercising the runtime guard for undefined
    expect(parseVariableExpression(undefined)).toBe("");
  });
});
