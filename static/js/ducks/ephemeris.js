import * as API from "../API";

const FETCH_EPHEMERIS = "skyportal/FETCH_EPHEMERIS";

// eslint-disable-next-line import/prefer-default-export
export function fetchEphemeris(ephemerisUrl) {
  return API.GET(ephemerisUrl, FETCH_EPHEMERIS);
}
