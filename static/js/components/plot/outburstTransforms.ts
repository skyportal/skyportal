// Client-side outburst transforms for the SSO light-curve tab: geometry- and
// colour-correct apparent magnitudes and compute the outburst statistic, live in
// the browser. Mirrors skyportal/utils/outburst.py (verified against the same
// sbpy HG12 fixtures in outburstTransforms.test.ts).
//
// The HG1G2 basis splines are stored as the precomputed piecewise-cubic
// coefficients from the Python implementation, so this only evaluates
// polynomials (no linear solve) and matches bit-for-bit.

interface Spline {
  nodes: number[];
  below: number[]; // linear extrapolation, evaluated at x
  segs: number[][]; // cubic per interval, evaluated at (x - nodes[i])
  above: number[]; // linear extrapolation, evaluated at x
}

const PHI1_SPLINE: Spline = {
  nodes: [
    0.1308996938995747, 0.5235987755982988, 1.0471975511965976,
    1.5707963267948966, 2.0943951023931953, 2.6179938779914944,
  ],
  below: [0.999999997761256, -1.9098593],
  segs: [
    [0.75, -1.9098593, 3.0632059507546687, -2.2709159732016233],
    [
      0.33486016, -0.5546343292135952, 0.38784609888094346,
      -0.11619084602803534,
    ],
    [0.1341056, -0.244045984668034, 0.20533394473291375, -0.0801973272976482],
    [
      0.051104756, -0.0949804384372285, 0.07936027759499992,
      -0.011595447695894826,
    ],
    [
      0.021465687, -0.021411423545129447, 0.06114619094674598,
      -0.1628628558176266,
    ],
  ],
  above: [0.24273744600146052, -0.091328612],
};
const PHI2_SPLINE: Spline = {
  nodes: [
    0.1308996938995747, 0.5235987755982988, 1.0471975511965976,
    1.5707963267948966, 2.0943951023931953, 2.6179938779914944,
  ],
  below: [1.0000000006373737, -0.5729578],
  segs: [
    [0.925, -0.5729578, -0.8900289744775439, 1.0914182852955112],
    [0.62884169, -0.7670536698010225, 0.3957679006766861, -0.12651132878679328],
    [
      0.31755495, -0.45665789065199525, 0.19704437012044826,
      -0.0369675374435365,
    ],
    [
      0.12716367, -0.28071808963896605, 0.1389758980934878,
      0.028512146018874328,
    ],
    [
      0.022373903, -0.11173256932741918, 0.18376267232897514,
      -0.09812349240793083,
    ],
  ],
  above: [0.0001652835379452825, -8.6573138e-8],
};
const PHI3_SPLINE: Spline = {
  nodes: [
    0.0, 0.005235987755982988, 0.017453292519943295, 0.03490658503988659,
    0.06981317007977318, 0.13962634015954636, 0.20943951023931956,
    0.3490658503988659, 0.5235987755982988,
  ],
  below: [1.0, -1.0630097],
  segs: [
    [1.0, -1.0630097, -9981.672512688505, 787411.2353356931],
    [0.83381185, -40.82886154020155, 2386.9542487348835, -62471.31537685938],
    [0.57735424, -10.478447335501123, 97.26095184116981, -498.53387383171105],
    [0.42144772, -7.538985955965683, 71.1577792479135, -311.4965283708852],
    [0.2317423, -3.709883035770421, 38.53793907629016, -167.78613617153775],
    [0.10348178, -0.7822794793311048, 3.396892891575516, -10.84738319409093],
    [0.061733473, -0.4665902472074776, 1.125022268026889, -0.8857418715332711],
    [
      0.016107006, -0.20422874491497908, 0.7540035804821168,
      -0.6452701244191253,
    ],
  ],
  above: [0.0, 0.0],
};

const polyval = (coef: number[], x: number): number =>
  coef.reduceRight((r, c) => r * x + c, 0);

const evalSpline = (sp: Spline, x: number): number => {
  const { nodes, segs } = sp;
  const last = nodes.length - 1;
  let y: number;
  if (x < nodes[0]!) {
    y = polyval(sp.below, x);
  } else if (x >= nodes[last]!) {
    y = polyval(sp.above, x);
  } else {
    let i = 0;
    while (i < last && !(x >= nodes[i]! && x < nodes[i + 1]!)) i += 1;
    y = polyval(segs[i]!, x - nodes[i]!);
  }
  return y < 0 ? 0 : y;
};

// HG12* reduced-magnitude phase function (mag), H=0, Penttila 2016.
export const hg12PhaseFunction = (phaseDeg: number, G12 = 0.5): number => {
  const a = (phaseDeg * Math.PI) / 180;
  const g1 = 0.84293649 * G12;
  const g2 = 0.5351335 * (1 - G12);
  const phi =
    g1 * evalSpline(PHI1_SPLINE, a) +
    g2 * evalSpline(PHI2_SPLINE, a) +
    (1 - g1 - g2) * evalSpline(PHI3_SPLINE, a);
  return -2.5 * Math.log10(phi);
};

// Offset (mag) bringing each point to the geometry of the last one.
export const scaleByGeometry = (
  rh: number[],
  delta: number[],
  phase: number[],
  rhSlope = -2,
  deltaSlope = -2,
): number[] => {
  const i = rh.length - 1;
  const rhRef = rh[i]!;
  const deltaRef = delta[i]!;
  const phiRef = hg12PhaseFunction(phase[i]!);
  return rh.map(
    (rhk, k) =>
      -2.5 *
        Math.log10(
          (rhRef / rhk) ** rhSlope * (deltaRef / delta[k]!) ** deltaSlope,
        ) +
      phiRef -
      hg12PhaseFunction(phase[k]!),
  );
};

const weightedMean = (x: number[], unc: number[]): [number, number] => {
  let sw = 0;
  let swx = 0;
  x.forEach((xk, k) => {
    const uk = unc[k]!;
    if (Number.isFinite(xk) && Number.isFinite(uk) && uk > 0) {
      const w = uk ** -2;
      sw += w;
      swx += w * xk;
    }
  });
  return sw === 0 ? [NaN, NaN] : [swx / sw, sw ** -0.5];
};

// Per-band colour offsets scaling each band to the test point's band. `m` must
// already be geometry-corrected; the test point (last) is excluded from averages.
export const colorScales = (
  m: number[],
  unc: number[],
  bands: string[],
): Record<string, number> => {
  const target = bands[bands.length - 1]!;
  const unique = Array.from(new Set(bands));
  const avg: Record<string, number> = {};
  unique.forEach((band) => {
    const xs: number[] = [];
    const us: number[] = [];
    bands.forEach((b, k) => {
      if (b === band && k !== bands.length - 1) {
        xs.push(m[k]!);
        us.push(unc[k]!);
      }
    });
    avg[band] = weightedMean(xs, us)[0];
  });
  const color: Record<string, number> = {};
  unique.forEach((band) => {
    color[band] = band === target ? 0 : avg[band]! - avg[target]!;
  });
  return color;
};

export interface OutburstReport {
  medianO: number;
  nPoints: number;
  testValue: number;
  dt: number[];
  bands: string[];
  unc: number[];
  m: number[]; // apparent
  H: number[]; // geometry-corrected
  Hcolor: number[]; // colour-removed
  ostats: number[];
  color: Record<string, number>;
}

const median = (a: number[]): number => {
  const v = a.filter((x) => Number.isFinite(x)).sort((p, q) => p - q);
  if (v.length === 0) return NaN;
  const mid = Math.floor(v.length / 2);
  return v.length % 2 ? v[mid]! : (v[mid - 1]! + v[mid]!) / 2;
};

export interface OutburstPoint {
  time: number;
  mag: number;
  magerr: number;
  band: string;
  rh: number;
  delta: number;
  phase: number;
}

// Run the statistic on the trailing `window` days (most recent point tested).
export const outburstReport = (
  points: OutburstPoint[],
  { window = 14, rhSlope = -2, deltaSlope = -2 } = {},
): OutburstReport | null => {
  const sorted = [...points].sort((a, b) => a.time - b.time);
  if (sorted.length < 2) return null;
  const tLast = sorted[sorted.length - 1]!.time;
  const win = sorted.filter(
    (p) => p.time - tLast > -window && p.time - tLast <= 0,
  );
  if (win.length < 2) return null;

  const time = win.map((p) => p.time);
  const m = win.map((p) => p.mag);
  const unc = win.map((p) => p.magerr);
  const bands = win.map((p) => p.band);
  const rh = win.map((p) => p.rh);
  const delta = win.map((p) => p.delta);
  const phase = win.map((p) => p.phase);
  const last = m.length - 1;
  const testBand = bands[last]!;
  const testMag = m[last]!;
  const testUnc = unc[last]!;

  if (!bands.slice(0, -1).includes(testBand)) return null; // no colour for test band

  const geom = scaleByGeometry(rh, delta, phase, rhSlope, deltaSlope);
  const H = m.map((mk, k) => mk + geom[k]!);
  const color = colorScales(H, unc, bands);
  const Hcolor = H.map((hk, k) => hk - color[bands[k]!]!);

  const ostats: number[] = [];
  for (let k = 0; k < last; k++) {
    const x = Hcolor[k]! - testMag;
    const y = Math.sqrt(testUnc ** 2 + unc[k]! ** 2);
    ostats.push(x / y);
  }

  return {
    medianO: median(ostats),
    nPoints: m.length,
    testValue: testMag,
    dt: time.map((t) => t - tLast),
    bands,
    unc,
    m,
    H,
    Hcolor,
    ostats,
    color,
  };
};
