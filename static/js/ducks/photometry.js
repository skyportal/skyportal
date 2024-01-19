import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SOURCE_PHOTOMETRY = "skyportal/FETCH_SOURCE_PHOTOMETRY";
const FETCH_SOURCE_PHOTOMETRY_OK = "skyportal/FETCH_SOURCE_PHOTOMETRY_OK";
const FETCH_FILTER_WAVELENGTHS = "skyportal/FETCH_FILTER_WAVELENGTHS";
const FETCH_ALL_ORIGINS = "skyportal/FETCH_ALL_ORIGINS";
const FETCH_ALL_ORIGINS_OK = "skyportal/FETCH_ALL_ORIGINS_OK";

const DELETE_PHOTOMETRY = "skyportal/DELETE_PHOTOMETRY";

const SUBMIT_PHOTOMETRY = "skyportal/SUBMIT_PHOTOMETRY";

const UPDATE_PHOTOMETRY = "skyportal/UPDATE_PHOTOMETRY";

// eslint-disable-next-line import/prefer-default-export
export function fetchSourcePhotometry(id) {
  return API.GET(`/api/sources/${id}/photometry`, FETCH_SOURCE_PHOTOMETRY, {
    includeOwnerInfo: true,
    deduplicatePhotometry: true,
  });
}

export function fetchFilterWavelengths(filterParams = {}) {
  return API.GET(
    `/api/internal/wavelengths`,
    FETCH_FILTER_WAVELENGTHS,
    filterParams,
  );
}

export function fetchAllOrigins() {
  return API.GET("/api/photometry/origins", FETCH_ALL_ORIGINS);
}

export function deletePhotometry(id) {
  return API.DELETE(`/api/photometry/${id}`, DELETE_PHOTOMETRY);
}

export function submitPhotometry(photometry) {
  return API.POST("/api/photometry", SUBMIT_PHOTOMETRY, photometry);
}

export function updatePhotometry(id, photometry) {
  return API.PATCH(`/api/photometry/${id}`, UPDATE_PHOTOMETRY, photometry);
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
    case FETCH_ALL_ORIGINS_OK: {
      const origins = action.data;
      return {
        ...state,
        origins,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("photometry", reducer);
