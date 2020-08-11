import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_SOURCE_SPECTRA = "skyportal/FETCH_SOURCE_SPECTRA";
export const FETCH_SOURCE_SPECTRA_OK = "skyportal/FETCH_SOURCE_SPECTRA_OK";

export function fetchSourceSpectra(id) {
  return API.GET(`/api/sources/${id}/spectra`, FETCH_SOURCE_SPECTRA);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_SOURCE_SPECTRA) {
    dispatch(fetchSourceSpectra(payload.obj_id));
  }
});

const reducer = (state = {}, action) => {
  switch (action.type) {
    case FETCH_SOURCE_SPECTRA_OK: {
      const spectra = action.data;
      if (spectra.length > 0) {
        const sourceID = spectra[0].obj_id;
        return {
          ...state,
          [sourceID]: spectra,
        };
      } else {
        return state;
      }
    }
    default:
      return state;
  }
};

store.injectReducer("spectra", reducer);
