import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_SOURCE_SPECTRA = "skyportal/FETCH_SOURCE_SPECTRA";
export const FETCH_SOURCE_SPECTRA_OK = "skyportal/FETCH_SOURCE_SPECTRA_OK";

export const UPLOAD_SOURCE_SPECTRUM_ASCII =
  "skyportal/UPLOAD_SOURCE_SPECTRUM_ASCII";
export const UPLOAD_SOURCE_SPECTRUM_ASCII_OK =
  "skyportal/UPLOAD_SOURCE_SPECTRUM_ASCII_OK";

export const PARSE_SOURCE_SPECTRUM_ASCII =
  "skyportal/PARSE_SOURCE_SPECTRUM_ASCII";
export const PARSE_SOURCE_SPECTRUM_ASCII_OK =
  "skyportal/PARSE_SOURCE_SPECTRUM_ASCII_OK";
export const PARSE_SOURCE_SPECTRUM_ASCII_ERROR =
  "skyportal/PARSE_SOURCE_SPECTRUM_ASCII_ERROR";

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

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_SOURCE_SPECTRA) {
    dispatch(fetchSourceSpectra(payload.obj_id));
  }
  if (actionType === PARSE_SOURCE_SPECTRUM_ASCII_ERROR) {
    dispatch({ type: RESET_PARSED_SPECTRUM });
  }
});

const reducer = (state = { parsed: null }, action) => {
  switch (action.type) {
    case FETCH_SOURCE_SPECTRA_OK: {
      const spectra = action.data;
      if (spectra.length > 0) {
        const sourceID = spectra[0].obj_id;
        return {
          ...state,
          [sourceID]: spectra,
        };
      }
      return state;
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
    default:
      return state;
  }
};

store.injectReducer("spectra", reducer);
