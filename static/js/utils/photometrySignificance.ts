import { LOW_SIGNIFICANCE_SNR } from "./constants";

/**
 * A measurement too faint to be a detection, rewritten as an upper limit.
 *
 * Below LOW_SIGNIFICANCE_SNR a point is real data but not a detection. Drawn at
 * its measured value it carries an error bar wider than the whole light curve,
 * squashing every other point; drawn at its limiting magnitude it says what it
 * actually establishes. Returns the point unchanged when it is already a limit
 * or has no error to judge it by.
 */
export const asDetectionOrLimit = (datum: any) => {
  if (datum.mag === null || datum.magerr == null || datum.magerr <= 0) {
    return datum;
  }
  // snr = flux / fluxerr, and fluxerr / flux is magerr / (2.5 / ln 10), so the
  // magnitudes give the signal-to-noise without going through flux.
  const snr = 2.5 / Math.LN10 / datum.magerr;
  if (snr >= LOW_SIGNIFICANCE_SNR) {
    return datum;
  }
  return { ...datum, mag: null, magerr: null };
};

export default { asDetectionOrLimit };
