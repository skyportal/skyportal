import * as API from "../API";

export const FETCH_EPHEMERIS = "skyportal/FETCH_EPHEMERIS";
export const FETCH_EPHEMERIS_OK = "skyportal/FETCH_EPHEMERIS_OK";

function fetchEphemeris(ephemerisUrl) {
  return API.GET(ephemerisUrl, FETCH_EPHEMERIS);
}

export default fetchEphemeris;
