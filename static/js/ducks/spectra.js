import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_SOURCE_SPECTRA = "skyportal/REFRESH_SOURCE_SPECTRA";
export const FETCH_SOURCE_SPECTRA = "skyportal/FETCH_SOURCE_SPECTRA";
export const FETCH_SOURCE_SPECTRA_OK = "skyportal/FETCH_SOURCE_SPECTRA_OK";

const DELETE_SPECTRUM = "skyportal/DELETE_SPECTRUM";
const UPLOAD_SPECTRUM = "skyportal/UPLOAD_SPECTRUM";
const UPLOAD_SPECTRUM_OK = "skyportal/UPLOAD_SPECTRUM_OK";

const PARSE_SOURCE_SPECTRUM_ASCII = "skyportal/PARSE_SOURCE_SPECTRUM_ASCII";
const PARSE_SOURCE_SPECTRUM_ASCII_OK =
  "skyportal/PARSE_SOURCE_SPECTRUM_ASCII_OK";

export const RESET_PARSED_SPECTRUM = "skyportal/RESET_PARSED_SPECTRUM";

export function fetchSourceSpectra(id) {
  return API.GET(`/api/sources/${id}/spectra`, FETCH_SOURCE_SPECTRA);
}

export function parseASCIISpectrum(data) {
  return API.POST(
    `/api/spectrum/parse/ascii`,
    PARSE_SOURCE_SPECTRUM_ASCII,
    data
  );
}

export function deleteSpectrum(id) {
  return API.DELETE(`/api/spectrum/${id}`, DELETE_SPECTRUM);
}

export function uploadASCIISpectrum(data) {
  return API.POST(`/api/spectrum/ascii`, UPLOAD_SPECTRUM, data);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_SOURCE_SPECTRA) {
    const state = getState().spectra;

    if (Object.keys(state).includes(payload.obj_id)) {
      dispatch(fetchSourceSpectra(payload.obj_id));
    }
  }
});

const reducer = (state = { parsed: null }, action) => {
  switch (action.type) {
    case FETCH_SOURCE_SPECTRA_OK: {
      const payload = action.data;
      const sourceID = payload.obj_id;
      return {
        parsed: state.parsed,
        [sourceID]: payload.spectra,
      };
    }
    case PARSE_SOURCE_SPECTRUM_ASCII_OK: {
      const parsed = action.data;
      return {
        ...state,
        parsed,
      };
    }
    case RESET_PARSED_SPECTRUM: {
      return {
        ...state,
        parsed: null,
      };
    }
    case UPLOAD_SPECTRUM_OK: {
      return {
        ...state,
        parsed: null,
      };
    }

    default:
      return state;
  }
};

store.injectReducer("spectra", reducer);
