import { describe, expect, it } from "bun:test";

import { LOW_SIGNIFICANCE_SNR, PHOT_ZP } from "./constants";
import { asDetectionOrLimit } from "./photometrySignificance";

// The magerr at exactly LOW_SIGNIFICANCE_SNR: snr = (2.5 / ln 10) / magerr.
const THRESHOLD_MAGERR = 2.5 / Math.LN10 / LOW_SIGNIFICANCE_SNR;

const point = (mag: number | null, magerr: number | null) => ({
  mag,
  magerr,
  limiting_mag: 20.5,
  mjd: 60000,
});

describe("faint measurements become limits", () => {
  it("drops the value of a measurement below the threshold", () => {
    // Plotted as measured, a 1-mag error bar spans the whole light curve.
    const converted = asDetectionOrLimit(point(20.0, 1.0));
    expect(converted.mag).toBeNull();
    expect(converted.magerr).toBeNull();
  });

  it("keeps the limiting magnitude, which is where it is then drawn", () => {
    expect(asDetectionOrLimit(point(20.0, 1.0)).limiting_mag).toBe(20.5);
  });

  it("keeps a measurement at or above the threshold", () => {
    const converted = asDetectionOrLimit(point(20.0, THRESHOLD_MAGERR * 0.99));
    expect(converted.mag).toBe(20.0);
  });

  it("converts one just below the threshold", () => {
    expect(
      asDetectionOrLimit(point(20.0, THRESHOLD_MAGERR * 1.01)).mag,
    ).toBeNull();
  });
});

describe("what it leaves alone", () => {
  it("passes an existing upper limit through", () => {
    expect(asDetectionOrLimit(point(null, null)).mag).toBeNull();
  });

  it("passes a point with no error through", () => {
    // Without an error there is no signal-to-noise to judge it by, and
    // discarding the value would lose a real measurement.
    expect(asDetectionOrLimit(point(20.0, null)).mag).toBe(20.0);
    expect(asDetectionOrLimit(point(20.0, 0)).mag).toBe(20.0);
  });

  it("does not mutate the point it was given", () => {
    const original = point(20.0, 1.0);
    asDetectionOrLimit(original);
    expect(original.mag).toBe(20.0);
  });
});

describe("it is the same rule the source page applies", () => {
  it("matches the flux-space computation", () => {
    // The source page goes via flux: fluxerr = (magerr / (2.5/ln10)) * flux,
    // snr = flux / fluxerr. Both must call the same points detections.
    for (const magerr of [0.05, 0.2, 0.36, 0.362, 0.5, 1.0, 3.0]) {
      const mag = 20.0;
      const flux = 10 ** (-0.4 * (mag - PHOT_ZP));
      const fluxerr = (magerr / (2.5 / Math.LN10)) * flux;
      const sourcePageSnr = flux / fluxerr;
      const converted = asDetectionOrLimit(point(mag, magerr));
      const keptAsDetection = converted.mag !== null;
      expect(keptAsDetection).toBe(sourcePageSnr >= LOW_SIGNIFICANCE_SNR);
    }
  });
});
