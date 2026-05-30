import * as API from "../API";

const FETCH_EPHEMERIDES = "skyportal/FETCH_EPHEMERIDES";

export function fetchEphemerides(telescopeIds: any) {
  return API.GET(`/api/internal/ephemeris`, FETCH_EPHEMERIDES, {
    telescopeIds,
  });
}
