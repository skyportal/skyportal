import * as API from "../API";

const FETCH_INSTRUMENT_LOG_EXTERNAL = "skyportal/FETCH_INSTRUMENT_EXTERNAL_LOG";

export const fetchInstrumentLogExternal = (
  id: number | string,
  params: Record<string, any> = {},
) =>
  API.GET(
    `/api/instrument/${id}/external_api`,
    FETCH_INSTRUMENT_LOG_EXTERNAL,
    params,
  );
