import { describe, expect, it } from "bun:test";

import {
  hg12PhaseFunction,
  outburstReport,
  OutburstPoint,
} from "./outburstTransforms";

// (phase angle deg, reduced magnitude) from sbpy HG12_Pen16.evaluate(a, 0, 0.5);
// identical to the Python fixtures so the two implementations stay in lockstep.
const HG12_FIXTURES: [number, number][] = [
  [0.0, 0.0000000008],
  [0.3, 0.0633709047],
  [1.0, 0.1740955589],
  [2.0, 0.2605581834],
  [4.0, 0.396288001],
  [7.5, 0.5582150592],
  [10.0, 0.6519205937],
  [20.0, 0.9873850487],
  [30.0, 1.2737341391],
  [45.0, 1.6870530694],
  [60.0, 2.1231979283],
  [90.0, 3.1380201178],
  [120.0, 4.5573412276],
  [150.0, 7.0046078063],
];

describe("hg12PhaseFunction", () => {
  it("matches sbpy HG12_Pen16 across phase angles", () => {
    HG12_FIXTURES.forEach(([alpha, expected]) => {
      expect(hg12PhaseFunction(alpha)).toBeCloseTo(expected, 6);
    });
  });
});

const flatWindow = (): OutburstPoint[] =>
  Array.from({ length: 14 }, (_, k) => ({
    time: k, // dt spans -13..0, all in a 14-day window
    mag: k % 2 === 0 ? 16.6 : 17.0, // g/r with a -0.4 colour
    magerr: 0.1,
    band: k % 2 === 0 ? "g" : "r",
    rh: 1,
    delta: 1,
    phase: 0,
  }));

describe("outburstReport", () => {
  it("reports no outburst for a flat, colour-offset light curve", () => {
    const r = outburstReport(flatWindow())!;
    expect(r.nPoints).toBe(14);
    expect(r.medianO).toBeCloseTo(0, 9);
    // colour removal collapses the two bands
    const spread = Math.max(...r.Hcolor) - Math.min(...r.Hcolor);
    expect(spread).toBeCloseTo(0, 9);
  });

  it("detects a brightening of the most recent point", () => {
    const pts = flatWindow();
    pts[pts.length - 1].mag = 17.0 - 0.5; // most recent r point 0.5 mag brighter
    const r = outburstReport(pts)!;
    expect(r.medianO).toBeCloseTo(0.5 / (0.1 * Math.sqrt(2)), 9);
  });

  it("orders points and drops those outside the window", () => {
    const pts = flatWindow();
    pts.push({
      time: -30,
      mag: 10,
      magerr: 0.1,
      band: "r",
      rh: 1,
      delta: 1,
      phase: 0,
    });
    const r = outburstReport(pts)!;
    expect(r.nPoints).toBe(14); // the out-of-window point is dropped
    expect(r.dt[r.dt.length - 1]).toBeCloseTo(0, 9); // test point is most recent
  });
});
