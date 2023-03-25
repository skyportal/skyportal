import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_INSTRUMENTS = "skyportal/REFRESH_INSTRUMENTS";

const FETCH_INSTRUMENTS = "skyportal/FETCH_INSTRUMENTS";
const FETCH_INSTRUMENTS_OK = "skyportal/FETCH_INSTRUMENTS_OK";

const FETCH_INSTRUMENT_FORMS = "skyportal/FETCH_INSTRUMENT_FORMS";
const FETCH_INSTRUMENT_FORMS_OK = "skyportal/FETCH_INSTRUMENT_FORMS_OK";

const FETCH_INSTRUMENT_OBSPLAN_FORMS =
  "skyportal/FETCH_INSTRUMENT_OBSPLAN_FORMS";
const FETCH_INSTRUMENT_OBSPLAN_FORMS_OK =
  "skyportal/FETCH_INSTRUMENT_OBSPLAN_FORMS_OK";

const FETCH_GCNEVENT_INSTRUMENTS = "skyportal/FETCH_GCNEVENT_INSTRUMENTS";
const FETCH_GCNEVENT_INSTRUMENTS_OK = "skyportal/FETCH_GCNEVENT_INSTRUMENTS_OK";

export function fetchGcnEventInstruments(dateobs, filterParams = {}) {
  filterParams.localizationDateobs = dateobs;
  filterParams.includeGeoJSONSummary = true;
  filterParams.includeGeoJSON = false;
  return API.GET("/api/instrument", FETCH_GCNEVENT_INSTRUMENTS, filterParams);
}

export const fetchInstruments = (filterParams = {}) =>
  API.GET("/api/instrument", FETCH_INSTRUMENTS, filterParams);

export const fetchInstrumentForms = () =>
  API.GET("/api/internal/instrument_forms", FETCH_INSTRUMENT_FORMS, {
    apiType: "api_classname",
  });

export const fetchInstrumentObsplanForms = () =>
  API.GET("/api/internal/instrument_forms", FETCH_INSTRUMENT_OBSPLAN_FORMS, {
    apiType: "api_classname_obsplan",
  });

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_INSTRUMENTS) {
    dispatch(fetchInstruments());
  }
});

const reducer = (
  state = {
    instrumentList: [],
    instrumentFormParams: {},
    instrumentObsplanFormParams: {},
    gcnEventInstruments: [],
  },
  action
) => {
  switch (action.type) {
    case FETCH_INSTRUMENTS_OK: {
      const instruments = action.data;
      return {
        ...state,
        instrumentList: instruments,
      };
    }
    case FETCH_INSTRUMENT_FORMS_OK: {
      const instrumentFormParams = action.data;
      return {
        ...state,
        instrumentFormParams,
      };
    }
    case FETCH_INSTRUMENT_OBSPLAN_FORMS_OK: {
      const instrumentObsplanFormParams = action.data;
      return {
        ...state,
        instrumentObsplanFormParams,
      };
    }
    case FETCH_GCNEVENT_INSTRUMENTS_OK: {
      return {
        ...state,
        gcnEventInstruments: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("instruments", reducer);
