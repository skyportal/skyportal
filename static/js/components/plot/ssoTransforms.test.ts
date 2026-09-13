import { describe, expect, it } from "bun:test";

import {
  fitBandColors,
  fittable,
  hg12PhaseFunction,
  outburstReport,
  SsoPoint,
  reduceToUnitGeometry,
  scaleByGeometry,
  histogram,
} from "./ssoTransforms";

// (phase angle deg, reduced mag) from sbpy HG12_Pen16.evaluate(a, 0, 0.5).
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

const flatWindow = (): SsoPoint[] =>
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

describe("reduceToUnitGeometry", () => {
  it("leaves a point already at unit geometry and zero phase alone", () => {
    expect(reduceToUnitGeometry([18], [1], [1], [0])[0]).toBeCloseTo(18, 6);
  });

  it("removes the inverse-square fall-off with distance", () => {
    // rh = delta = 2 au is 5*log10(2*2) = 3.01 mag fainter than at unit geometry.
    const [reduced] = reduceToUnitGeometry([18], [2], [2], [0]);
    expect(reduced).toBeCloseTo(18 - 5 * Math.log10(4), 6);
  });

  it("corrects harder for distance as the activity slope steepens", () => {
    const inert = reduceToUnitGeometry([18], [3], [2], [0])[0]!;
    const active = reduceToUnitGeometry([18], [3], [2], [0], {
      rhSlope: -4,
    })[0]!;
    // A steeper slope removes more fall-off, so the reduced magnitude lands brighter.
    expect(active).toBeLessThan(inert);
    expect(active - inert).toBeCloseTo(-5 * Math.log10(3), 6);
  });

  it("optionally leaves the phase function in, giving H(1,1,alpha)", () => {
    const withPhase = reduceToUnitGeometry([18], [1], [1], [20])[0]!;
    const without = reduceToUnitGeometry([18], [1], [1], [20], {
      removePhase: false,
    })[0]!;
    expect(without - withPhase).toBeCloseTo(hg12PhaseFunction(20), 6);
  });

  it("agrees with the relative correction up to a constant", () => {
    // Both views of one curve must agree in shape.
    const rh = [2.5, 2.2, 1.9];
    const delta = [1.8, 1.5, 1.4];
    const phase = [12, 18, 25];
    const m = [19.1, 18.6, 18.2];
    const relative = scaleByGeometry(rh, delta, phase).map((o, k) => m[k]! + o);
    const absolute = reduceToUnitGeometry(m, rh, delta, phase);
    const offsets = relative.map((v, k) => v - absolute[k]!);
    offsets.forEach((o) => expect(o).toBeCloseTo(offsets[0]!, 6));
  });

  it("returns NaN rather than nonsense for a missing distance", () => {
    expect(reduceToUnitGeometry([18], [0], [1], [0])[0]).toBeNaN();
    expect(reduceToUnitGeometry([18], [1], [NaN], [0])[0]).toBeNaN();
  });
});

describe("reducing a synthetic object", () => {
  it("recovers a constant H from observations across two apparitions", () => {
    // Fixed brightness at wildly varying geometry must reduce flat.
    const H = 15.0;
    const geometry: [number, number, number][] = [
      [2.6, 1.7, 8],
      [2.4, 1.5, 14],
      [2.2, 1.3, 21],
      [3.0, 2.1, 5],
      [2.8, 1.9, 11],
      [2.5, 1.6, 19],
    ];
    const rh = geometry.map(([r]) => r);
    const delta = geometry.map(([, d]) => d);
    const phase = geometry.map(([, , a]) => a);
    const observed = geometry.map(
      ([r, d, a]) => H + 5 * Math.log10(r * d) + hg12PhaseFunction(a),
    );

    reduceToUnitGeometry(observed, rh, delta, phase).forEach((v) =>
      expect(v).toBeCloseTo(H, 8),
    );
  });
});

describe("fitBandColors", () => {
  /** An observation on a given night. Geometry depends on the night alone, so
   *  two bands observed the same night share it exactly and a recovered colour
   *  is exact rather than carrying a within-night residual. */
  const point = (
    night: number,
    band: string,
    mag: number,
    hours = 0,
  ): SsoPoint => ({
    time: night + hours / 24,
    mag,
    magerr: 0.02,
    band,
    rh: 2 + 0.01 * night,
    delta: 1.5 + 0.01 * night,
    phase: 10 + 0.05 * night,
  });

  it("recovers a known colour from paired nights", () => {
    // Pairing within a night is what separates the colour from the trend.
    const points = [0, 1, 2, 3].flatMap((n) => [
      point(n, "r", 18 + 0.1 * n),
      point(n, "g", 18.5 + 0.1 * n, 1),
    ]);
    const fit = fitBandColors(points)!;
    // Equal nights and equal points, so the tie goes to r.
    expect(fit.reference).toBe("r");
    expect(fit.colors.g!.offset - fit.colors.r!.offset).toBeCloseTo(0.5, 9);
    expect(fit.colors.g!.nights).toBe(4);
  });

  it("is not fooled by bands sampling different geometry", () => {
    // Disjoint epochs: differencing whole-curve means would absorb the trend.
    const paired = [10, 11, 12].flatMap((n) => [
      point(n, "r", 18),
      point(n, "g", 18.4, 1),
    ]);
    const lopsided = [point(0, "r", 17.2), point(40, "g", 19.6)];
    const fit = fitBandColors([...paired, ...lopsided])!;
    expect(Math.abs(fit.colors.g!.offset - fit.colors.r!.offset)).toBeCloseTo(
      0.4,
      9,
    );
  });

  it("counts only the nights where both bands were seen", () => {
    const points = [
      point(0, "r", 18),
      point(0, "g", 18.4, 1),
      point(1, "r", 18),
      point(2, "r", 18),
      point(3, "g", 18.4),
    ];
    const fit = fitBandColors(points)!;
    expect(fit.reference).toBe("r"); // 3 nights, against g's 2
    expect(fit.colors.g!.nights).toBe(1);
  });

  it("gives a colour from one night, but no uncertainty for it", () => {
    const fit = fitBandColors([point(0, "r", 18), point(0, "g", 18.4, 1)])!;
    expect(fit.reference).toBe("r");
    expect(fit.colors.g!.nights).toBe(1);
    expect(fit.colors.g!.uncertainty).toBeNaN();
  });

  it("shrinks the uncertainty as nights accumulate", () => {
    const scatter = [0.02, -0.02, 0.01, -0.01, 0.03, -0.03];
    const nights = (n: number) =>
      scatter
        .slice(0, n)
        .flatMap((noise, k) => [
          point(k, "r", 18),
          point(k, "g", 18.4 + noise, 1),
        ]);
    const few = fitBandColors(nights(3))!.colors.g!.uncertainty;
    const many = fitBandColors(nights(6))!.colors.g!.uncertainty;
    expect(many).toBeLessThan(few);
  });

  it("returns null when there is nothing usable", () => {
    expect(fitBandColors([])).toBeNull();
  });
});

describe("choosing the reference band", () => {
  const at = (night: number, band: string): SsoPoint => ({
    time: night,
    mag: 18,
    magerr: 0.02,
    band,
    rh: 2,
    delta: 1.5,
    phase: 10,
  });

  it("prefers the band seen on the most nights", () => {
    const points = [at(0, "g"), at(1, "g"), at(2, "g"), at(0, "u")];
    expect(fitBandColors(points)!.reference).toBe("g");
  });

  it("breaks an exact tie on convention, not alphabetically", () => {
    // g would win on name; r is what these colours are quoted against.
    const points = [0, 1].flatMap((n) => [at(n, "g"), at(n, "r")]);
    expect(fitBandColors(points)!.reference).toBe("r");
  });
});

describe("rejected photometry", () => {
  const at = (
    night: number,
    band: string,
    mag: number,
    rejected = false,
  ): SsoPoint => ({
    time: night,
    mag,
    magerr: 0.02,
    band,
    rh: 2,
    delta: 1.5,
    phase: 10,
    rejected,
  });

  it("is dropped before anything is fitted", () => {
    expect(fittable([at(0, "r", 18), at(1, "r", 99, true)])).toHaveLength(1);
  });

  it("cannot drag a fitted colour", () => {
    const good = [0, 1, 2].flatMap((n) => [at(n, "r", 18), at(n, "g", 18.4)]);
    const clean = fitBandColors(good)!;
    // A wildly wrong g point on a fourth night, marked rejected.
    const withJunk = [...good, at(3, "r", 18), at(3, "g", 25, true)];
    const fitted = fitBandColors(withJunk)!;
    expect(fitted.colors.g!.offset).toBeCloseTo(clean.colors.g!.offset, 9);
    // And it does not count towards the nights the colour rests on.
    expect(fitted.colors.g!.nights).toBe(clean.colors.g!.nights);
  });

  it("cannot raise a false outburst", () => {
    const flat = [0, 1, 2, 3, 4].map((n) => at(n, "r", 18));
    const spike = [...flat, at(5, "r", 14, true)];
    // The rejected spike is the most recent point, the one the statistic tests.
    const report = outburstReport(spike)!;
    expect(Math.abs(report.medianO)).toBeLessThan(1);
  });
});

describe("histogram", () => {
  it("bins values into bars that account for every point", () => {
    const values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
    const h = histogram(values, 5);
    expect(h.counts).toEqual([2, 2, 2, 2, 2]);
    expect(h.counts.reduce((a, b) => a + b, 0)).toBe(values.length);
    expect(h.centers).toHaveLength(5);
  });

  it("puts the maximum in the last bin rather than past the end", () => {
    const h = histogram([0, 10], 4);
    expect(h.counts[h.counts.length - 1]).toBe(1);
    expect(h.counts.reduce((a, b) => a + b, 0)).toBe(2);
  });

  it("gives a single distinct value one bar", () => {
    const h = histogram([3, 3, 3], 20);
    expect(h.counts).toEqual([3]);
    expect(h.centers).toEqual([3]);
  });

  it("ignores non-finite values and survives an empty input", () => {
    expect(
      histogram([1, NaN, 2, Infinity], 2).counts.reduce((a, b) => a + b, 0),
    ).toBe(2);
    expect(histogram([], 5).counts).toEqual([]);
  });
});
