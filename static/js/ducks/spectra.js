import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_SOURCE_SPECTRA = "skyportal/REFRESH_SOURCE_SPECTRA";
export const FETCH_SOURCE_SPECTRA = "skyportal/FETCH_SOURCE_SPECTRA";
export const FETCH_SOURCE_SPECTRA_OK = "skyportal/FETCH_SOURCE_SPECTRA_OK";

const DELETE_SPECTRUM = "skyportal/DELETE_SPECTRUM";
const UPLOAD_SPECTRUM = "skyportal/UPLOAD_SPECTRUM";
const UPLOAD_SPECTRUM_OK = "skyportal/UPLOAD_SPECTRUM_OK";

const DELETE_ANNOTATION_SPECTRUM = "skyportal/DELETE_ANNOTATION_SPECTRUM";

const PARSE_SOURCE_SPECTRUM_ASCII = "skyportal/PARSE_SOURCE_SPECTRUM_ASCII";
const PARSE_SOURCE_SPECTRUM_ASCII_OK =
  "skyportal/PARSE_SOURCE_SPECTRUM_ASCII_OK";

export const RESET_PARSED_SPECTRUM = "skyportal/RESET_PARSED_SPECTRUM";

const ADD_SYNTHETIC_PHOTOMETRY = "skyportal/ADD_SYNTHETIC_PHOTOMETRY";

const ADD_SPECTRUM_TNS = "skyportal/ADD_SPECTRUM_TNS";

export function fetchSourceSpectra(id, normalization = null) {
  if (normalization) {
    return API.GET(
      `/api/sources/${id}/spectra?normalization=${normalization}&sortBy=observed_at&order=asc`,
      FETCH_SOURCE_SPECTRA,
    );
  }
  return API.GET(`/api/sources/${id}/spectra`, FETCH_SOURCE_SPECTRA);
}

export function parseASCIISpectrum(data) {
  return API.POST(
    `/api/spectrum/parse/ascii`,
    PARSE_SOURCE_SPECTRUM_ASCII,
    data,
  );
}

export function addSyntheticPhotometry(id, formData = {}) {
  return API.POST(
    `/api/spectra/synthphot/${id}`,
    ADD_SYNTHETIC_PHOTOMETRY,
    formData,
  );
}

export function addSpectrumTNS(id, formData = {}) {
  return API.POST(`/api/spectrum/tns/${id}`, ADD_SPECTRUM_TNS, formData);
}

export function deleteSpectrum(id) {
  return API.DELETE(`/api/spectrum/${id}`, DELETE_SPECTRUM);
}

export function uploadASCIISpectrum(data) {
  return API.POST(`/api/spectrum/ascii`, UPLOAD_SPECTRUM, data);
}

export function deleteAnnotation(id, annotationID) {
  return API.DELETE(
    `/api/spectra/${id}/annotations/${annotationID}`,
    DELETE_ANNOTATION_SPECTRUM,
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_SOURCE_SPECTRA) {
    const state = getState().spectra;

    Object.entries(state).forEach(([objID, spectra]) => {
      if (
        spectra?.[0]?.obj_internal_key === payload.obj_internal_key &&
        payload?.obj_internal_key !== null
      ) {
        dispatch(fetchSourceSpectra(objID));
      }
    });
  }
});

const reducer = (state = { parsed: null }, action) => {
  switch (action.type) {
    case FETCH_SOURCE_SPECTRA_OK: {
      const payload = action.data;
      const sourceID = payload.obj_id;
      return {
        ...state,
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
