// Sun and Moon adapted from SunCalc (https://github.com/mourner/suncalc), BSD-2-Clause.
const { PI, sin, cos, tan, asin, acos, atan2: atan, hypot } = Math;
const rad = PI / 180;
const obliquity = rad * 23.4397;
const sunDistanceKm = 149598000;

const toDays = (date) => date.valueOf() / 86400000 - 0.5 + 2440588 - 2451545;
const raDeg = (ra) => (((ra / rad) % 360) + 360) % 360;

const rightAscension = (l, b) =>
  atan(sin(l) * cos(obliquity) - tan(b) * sin(obliquity), cos(l));
const declination = (l, b) =>
  asin(sin(b) * cos(obliquity) + cos(b) * sin(obliquity) * sin(l));

function sunCoords(d) {
  const M = rad * (357.5291 + 0.98560028 * d);
  const C = rad * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M));
  const L = M + C + rad * 102.9372 + PI;
  return { ra: rightAscension(L, 0), dec: declination(L, 0) };
}

function moonCoords(d) {
  const M = rad * (134.963 + 13.064993 * d);
  const l = rad * (218.316 + 13.176396 * d) + rad * 6.289 * sin(M);
  const b = rad * 5.128 * sin(rad * (93.272 + 13.22935 * d));
  return {
    ra: rightAscension(l, b),
    dec: declination(l, b),
    distKm: 385001 - 20905 * cos(M),
  };
}

function sunPosition(date) {
  const { ra, dec } = sunCoords(toDays(date));
  return { ra: raDeg(ra), dec: dec / rad };
}

function moonPosition(date) {
  const s = sunCoords(toDays(date));
  const m = moonCoords(toDays(date));
  const dRa = s.ra - m.ra;
  const phi = acos(
    sin(s.dec) * sin(m.dec) + cos(s.dec) * cos(m.dec) * cos(dRa),
  );
  const inc = atan(
    sunDistanceKm * sin(phi),
    m.distKm - sunDistanceKm * cos(phi),
  );
  return {
    ra: raDeg(m.ra),
    dec: m.dec / rad,
    fraction: (1 + cos(inc)) / 2,
    angle: atan(
      cos(s.dec) * sin(dRa),
      sin(s.dec) * cos(m.dec) - cos(s.dec) * sin(m.dec) * cos(dRa),
    ),
  };
}

const galacticToEquatorialMatrix = [
  [-0.0548755604, 0.4941094279, -0.867666149],
  [-0.8734370902, -0.44482963, -0.1980763734],
  [-0.4838350155, 0.7469822445, 0.4559837762],
];

function galacticToEquatorial(l, b) {
  const g = [
    cos(b * rad) * cos(l * rad),
    cos(b * rad) * sin(l * rad),
    sin(b * rad),
  ];
  const [x, y, z] = galacticToEquatorialMatrix.map((row) =>
    row.reduce((sum, v, i) => sum + v * g[i], 0),
  );
  return [raDeg(atan(y, x)), asin(z) / rad];
}

const radPerUnit = { arcsec: rad / 3600, arcmin: rad / 60, deg: rad, rad: 1 };

function greatCircleDistance(
  ra1Deg,
  dec1Deg,
  ra2Deg,
  dec2Deg,
  unit = "arcsec",
) {
  const [ra1, dec1, ra2, dec2] = [ra1Deg, dec1Deg, ra2Deg, dec2Deg].map(
    (x) => x * rad,
  );
  const dRa = Math.abs(ra2 - ra1);
  const distance = atan(
    hypot(
      cos(dec2) * sin(dRa),
      cos(dec1) * sin(dec2) - sin(dec1) * cos(dec2) * cos(dRa),
    ),
    sin(dec1) * sin(dec2) + cos(dec1) * cos(dec2) * cos(dRa),
  );
  return distance / (radPerUnit[unit] ?? rad);
}

export { sunPosition, moonPosition, galacticToEquatorial, greatCircleDistance };
