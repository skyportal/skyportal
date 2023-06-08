import * as API from "../API";

const FETCH_INSTRUMENT_LOG_EXTERNAL = "skyportal/FETCH_INSTRUMENT_EXTERNAL_LOG";

// eslint-disable-next-line import/prefer-default-export
export const fetchInstrumentLogExternal = (id, params = {}) =>
  API.GET(
    `/api/instrument/${id}/external_api`,
    FETCH_INSTRUMENT_LOG_EXTERNAL,
    params
  );
