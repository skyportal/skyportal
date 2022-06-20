import * as API from "../API";

const FETCH_EPHEMERIDES = "skyportal/FETCH_EPHEMERIDES";

// eslint-disable-next-line import/prefer-default-export
export function fetchEphemerides(telescopeIds) {
  return API.GET(`/api/internal/ephemeris`, FETCH_EPHEMERIDES, {
    telescopeIds,
  });
}
