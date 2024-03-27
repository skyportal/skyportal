// Code taken from Vladimir Agafonkin's SunCalc library https://github.com/mourner/suncalc,
// which unfortunately does not export these methods.

const { PI } = Math;
const { sin } = Math;
const { cos } = Math;
const { tan } = Math;
const { asin } = Math;
const atan = Math.atan2;
const { acos } = Math;
const rad = PI / 180;

const moonRadius = 1737.4; // km
const sunRadius = 695700; // km

// sun calculations are based on http://aa.quae.nl/en/reken/zonpositie.html formulas

// date/time constants and conversions

const dayMs = 1000 * 60 * 60 * 24;
const J1970 = 2440588;
const J2000 = 2451545;

function toJulian(date) {
  return date.valueOf() / dayMs - 0.5 + J1970;
}
function fromJulian(j) {
  return new Date((j + 0.5 - J1970) * dayMs);
}
function toDays(date) {
  return toJulian(date) - J2000;
}

// general calculations for position

const e = rad * 23.4397; // obliquity of the Earth

function rightAscension(l, b) {
  return atan(sin(l) * cos(e) - tan(b) * sin(e), cos(l));
}
function declination(l, b) {
  return asin(sin(b) * cos(e) + cos(b) * sin(e) * sin(l));
}

function azimuth(H, phi, dec) {
  return atan(sin(H), cos(H) * sin(phi) - tan(dec) * cos(phi));
}
function altitude(H, phi, dec) {
  return asin(sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(H));
}

function siderealTime(d, lw) {
  return rad * (280.16 + 360.9856235 * d) - lw;
}

function astroRefraction(h) {
  if (h < 0)
    // the following formula works for positive altitudes only.
    h = 0; // if h = -0.08901179 a div/0 would occur.

  // formula 16.4 of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell, Richmond) 1998.
  // 1.02 / tan(h + 10.26 / (h + 5.10)) h in degrees, result in arc minutes -> converted to rad:
  return 0.0002967 / Math.tan(h + 0.00312536 / (h + 0.08901179));
}

// general sun calculations

function solarMeanAnomaly(d) {
  return rad * (357.5291 + 0.98560028 * d);
}

function eclipticLongitude(M) {
  const C = rad * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M)); // equation of center
  const P = rad * 102.9372; // perihelion of the Earth

  return M + C + P + PI;
}

function sunCoords(d) {
  d = toDays(d);

  const M = solarMeanAnomaly(d);
  const L = eclipticLongitude(M);
  const dt = 149598000;

  return {
    dec: declination(L, 0) * (180 / Math.PI),
    ra: rightAscension(L, 0) * (180 / Math.PI),
    dist: dt, // distance from Earth in km
    radiusDeg: (sunRadius / dt) * (180 / Math.PI),
  };
}

function moonCoords(d) {
  // geocentric ecliptic coordinates of the moon

  d = toDays(d);

  const L = rad * (218.316 + 13.176396 * d); // ecliptic longitude
  const M = rad * (134.963 + 13.064993 * d); // mean anomaly
  const F = rad * (93.272 + 13.22935 * d); // mean distance
  const l = L + rad * 6.289 * sin(M); // longitude
  const b = rad * 5.128 * sin(F); // latitude
  const dt = 385001 - 20905 * cos(M); // distance to the moon in km

  return {
    ra: rightAscension(l, b) * (180 / Math.PI),
    dec: declination(l, b) * (180 / Math.PI),
    dist: dt,
    radiusDeg: (moonRadius / dt) * (180 / Math.PI),
  };
}

function getMoonIllumination(d) {
  const s = sunCoords(d);
  const m = moonCoords(d);
  const sdist = 149598000; // distance from Earth to Sun in km
  const phi = acos(
    sin(s.dec) * sin(m.dec) + cos(s.dec) * cos(m.dec) * cos(s.ra - m.ra),
  );
  const inc = atan(sdist * sin(phi), m.dist - sdist * cos(phi));
  const angle = atan(
    cos(s.dec) * sin(s.ra - m.ra),
    sin(s.dec) * cos(m.dec) - cos(s.dec) * sin(m.dec) * cos(s.ra - m.ra),
  );

  return {
    fraction: (1 + cos(inc)) / 2,
    phase: 0.5 + (0.5 * inc * (angle < 0 ? -1 : 1)) / Math.PI,
    angle,
  };
}

function sunGeoJSON(d) {
  const coords = sunCoords(d);
  return {
    type: "Feature",
    geometry: {
      type: "Point",
      coordinates: [coords.ra, coords.dec],
    },
    properties: {
      radius: coords.radiusDeg,
      ra: coords.ra,
      dec: coords.dec,
      dist: coords.dist,
    },
  };
}

function moonGeoJSON(d) {
  const coords = moonCoords(d);
  const illumination = getMoonIllumination(d);

  return {
    type: "Feature",
    geometry: {
      type: "Point",
      coordinates: [coords.ra, coords.dec],
    },
    properties: {
      radius: coords.radiusDeg,
      ra: coords.ra,
      dec: coords.dec,
      dist: coords.dist,
      illumination,
    },
  };
}

// implement this python method to calculate a great circle distance in javascript:
// def great_circle_distance(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
// """
//     Distance between two points on the sphere
// :param ra1_deg:
// :param dec1_deg:
// :param ra2_deg:
// :param dec2_deg:
// :return: distance in degrees
// """
// # this is orders of magnitude faster than astropy.coordinates.Skycoord.separation
// DEGRA = np.pi / 180.0
// ra1, dec1, ra2, dec2 = (
//     ra1_deg * DEGRA,
//     dec1_deg * DEGRA,
//     ra2_deg * DEGRA,
//     dec2_deg * DEGRA,
// )
// delta_ra = np.abs(ra2 - ra1)
// distance = np.arctan2(
//     np.sqrt(
//         (np.cos(dec2) * np.sin(delta_ra)) ** 2
//         + (
//             np.cos(dec1) * np.sin(dec2)
//             - np.sin(dec1) * np.cos(dec2) * np.cos(delta_ra)
//         )
//         ** 2
//     ),
//     np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(delta_ra),
// )

// return distance * 180.0 / np.pi

function greatCircleDistance(
  ra1_deg,
  dec1_deg,
  ra2_deg,
  dec2_deg,
  unit = "arcsec",
) {
  const ra1 = ra1_deg * rad;
  const dec1 = dec1_deg * rad;
  const ra2 = ra2_deg * rad;
  const dec2 = dec2_deg * rad;

  const delta_ra = Math.abs(ra2 - ra1);
  const distance = Math.atan2(
    Math.sqrt(
      (Math.cos(dec2) * Math.sin(delta_ra)) ** 2 +
        (Math.cos(dec1) * Math.sin(dec2) -
          Math.sin(dec1) * Math.cos(dec2) * Math.cos(delta_ra)) **
          2,
    ),
    Math.sin(dec1) * Math.sin(dec2) +
      Math.cos(dec1) * Math.cos(dec2) * Math.cos(delta_ra),
  );

  switch (unit) {
    case "arcsec":
      return (distance * 180.0 * 3600) / Math.PI;
    case "deg":
      return (distance * 180.0) / Math.PI;
    case "arcmin":
      return (distance * 180.0 * 60) / Math.PI;
    case "rad":
      return distance;
    default:
      return (distance * 180.0) / Math.PI;
  }
}
export {
  toJulian,
  fromJulian,
  toDays,
  rightAscension,
  declination,
  azimuth,
  altitude,
  siderealTime,
  astroRefraction,
  solarMeanAnomaly,
  eclipticLongitude,
  sunCoords,
  moonCoords,
  sunGeoJSON,
  moonGeoJSON,
  greatCircleDistance,
};
