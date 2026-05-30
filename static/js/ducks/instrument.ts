import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_INSTRUMENT = "skyportal/REFRESH_INSTRUMENT";

const FETCH_INSTRUMENT = "skyportal/FETCH_INSTRUMENT";
const FETCH_INSTRUMENT_OK = "skyportal/FETCH_INSTRUMENT_OK";

const SUBMIT_INSTRUMENT = "skyportal/SUBMIT_INSTRUMENT";

const MODIFY_INSTRUMENT = "skyportal/MODIFY_INSTRUMENT";

const DELETE_INSTRUMENT = "skyportal/DELETE_INSTRUMENT";

const FETCH_INSTRUMENT_SKYMAP = "skyportal/FETCH_INSTRUMENT_SKYMAP";

const UPDATE_INSTRUMENT_STATUS = "skyportal/UPDATE_INSTRUMENT_STATUS";

const FETCH_INSTRUMENT_LOGS = "skyportal/FETCH_INSTRUMENT_LOGS";
const FETCH_INSTRUMENT_LOGS_OK = "skyportal/FETCH_INSTRUMENT_LOGS_OK";

export const fetchInstrument = (id: number | string) =>
  API.GET(`/api/instrument/${id}`, FETCH_INSTRUMENT);

export const submitInstrument = (run: any) =>
  API.POST(`/api/instrument`, SUBMIT_INSTRUMENT, run);

export const modifyInstrument = (id: number | string, params: any) =>
  API.PUT(`/api/instrument/${id}`, MODIFY_INSTRUMENT, params);

export function deleteInstrument(id: number | string) {
  return API.DELETE(`/api/instrument/${id}`, DELETE_INSTRUMENT);
}

export function fetchInstrumentSkymap(
  id: number | string,
  localization: any,
  airmassTime: any = null,
) {
  if (airmassTime) {
    return API.GET(
      `/api/instrument/${id}?includeGeoJSONSummary=True&localizationDateobs=${localization.dateobs}&localizationName=${localization.localization_name}&airmassTime=${airmassTime}`,
      FETCH_INSTRUMENT_SKYMAP,
    );
  }

  return API.GET(
    `/api/instrument/${id}?includeGeoJSONSummary=True&localizationDateobs=${localization.dateobs}&localizationName=${localization.localization_name}`,
    FETCH_INSTRUMENT_SKYMAP,
  );
}

export const updateInstrumentStatus = (id: number | string) =>
  API.PUT(`/api/instrument/${id}/status`, UPDATE_INSTRUMENT_STATUS);

export const fetchInstrumentLogs = (id: number | string, params: any) =>
  API.GET(`/api/instrument/${id}/log`, FETCH_INSTRUMENT_LOGS, params);

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: any, getState: any) => {
    const { instrument } = getState();
    if (actionType === REFRESH_INSTRUMENT) {
      const { instrument_id } = payload;
      if (parseInt(instrument_id, 10) === instrument?.id) {
        dispatch(fetchInstrument(instrument_id));
      }
    }
  },
);

interface InstrumentAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (state: Record<string, any> = {}, action: InstrumentAction) => {
  switch (action.type) {
    case FETCH_INSTRUMENT_OK: {
      const instrument = action.data;
      return {
        ...state,
        ...instrument,
      };
    }
    case FETCH_INSTRUMENT_LOGS_OK: {
      const logs = action.data;
      return {
        ...state,
        logs,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("instrument", reducer);
