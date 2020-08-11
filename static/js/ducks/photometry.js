import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_SOURCE_PHOTOMETRY = "skyportal/FETCH_SOURCE_PHOTOMETRY";
export const FETCH_SOURCE_PHOTOMETRY_OK =
  "skyportal/FETCH_SOURCE_PHOTOMETRY_OK";

export function fetchSourcePhotometry(id) {
  return API.GET(`/api/sources/${id}/photometry`, FETCH_SOURCE_PHOTOMETRY);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_SOURCE_PHOTOMETRY) {
    dispatch(fetchSourcePhotometry(payload.obj_id));
  }
});

const reducer = (state = {}, action) => {
  switch (action.type) {
    case FETCH_SOURCE_PHOTOMETRY_OK: {
      const photometry = action.data;
      if (photometry.length > 0) {
        const sourceID = photometry[0].obj_id;
        return {
          ...state,
          [sourceID]: photometry,
        };
      }
      return state;
    }
    default:
      return state;
  }
};

store.injectReducer("photometry", reducer);
