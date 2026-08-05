import { describe, it, expect } from "bun:test";

import { buildModelLightcurveTraces, ModelFit } from "./modelLightcurveTraces";

// A model overlay must be drawn in the same extinction frame as the plotted
// photometry: dereddened iff the toggle is on. A fit that ran on dereddened
// photometry is dereddened-native; one that didn't is observed-native. The
// builder shifts by A_lambda (=0.5 here) to reconcile the two.
const xOf = (mjd: number) => mjd;
const colors: Record<string, number[]> = { ztfg: [0, 0, 0] };
const A = { ztfg: 0.5 };

const fit = (dereddened: boolean): ModelFit => ({
  id: 1,
  dereddened,
  // [mjd, median, lo, hi]; second row is a NaN gap (null).
  model_lightcurve: {
    ztfg: [
      [59000, 20.0, 19.9, 20.1],
      [59001, null, null, null],
    ],
  } as any,
});

// The median line is the trace carrying a `name`; the band polygon has none.
const medianY = (
  fitObj: ModelFit,
  showExtinction: boolean,
): (number | null)[] => {
  const traces = buildModelLightcurveTraces(
    [fitObj],
    colors,
    xOf,
    "mag",
    A,
    showExtinction,
  );
  return traces.find((t) => typeof t.name === "string").y;
};

describe("buildModelLightcurveTraces extinction frame", () => {
  it("observed-native fit, toggle off: unchanged, gap preserved", () => {
    const y = medianY(fit(false), false);
    expect(y[0]).toBeCloseTo(20.0);
    expect(y[1]).toBeNull();
  });

  it("observed-native fit, toggle on: dereddened by A", () => {
    expect(medianY(fit(false), true)[0]).toBeCloseTo(19.5);
  });

  it("dereddened-native fit, toggle off: re-reddened by A", () => {
    expect(medianY(fit(true), false)[0]).toBeCloseTo(20.5);
  });

  it("dereddened-native fit, toggle on: unchanged", () => {
    expect(medianY(fit(true), true)[0]).toBeCloseTo(20.0);
  });

  it("no A_lambda for the filter: no shift either way", () => {
    const traces = buildModelLightcurveTraces(
      [fit(true)],
      colors,
      xOf,
      "mag",
      {},
      false,
    );
    expect(traces.find((t) => typeof t.name === "string").y[0]).toBeCloseTo(
      20.0,
    );
  });
});
