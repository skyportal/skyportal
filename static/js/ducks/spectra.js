import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_SOURCE_SPECTRA = "skyportal/FETCH_SOURCE_SPECTRA";
export const FETCH_SOURCE_SPECTRA_OK = "skyportal/FETCH_SOURCE_SPECTRA_OK";

export const UPLOAD_SPECTRUM = "skyportal/UPLOAD_SPECTRUM";
export const UPLOAD_SPECTRUM_OK = "skyportal/UPLOAD_SPECTRUM_OK";

export const PARSE_SOURCE_SPECTRUM_ASCII =
  "skyportal/PARSE_SOURCE_SPECTRUM_ASCII";
export const PARSE_SOURCE_SPECTRUM_ASCII_OK =
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

export function uploadSpectrumAscii(data) {
  return API.POST(`/api/spectrum/ascii`, UPLOAD_SPECTRUM, data);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_SOURCE_SPECTRA) {
    dispatch(fetchSourceSpectra(payload.obj_id));
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
