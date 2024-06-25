import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SOURCE_PHOTOMETRY = "skyportal/FETCH_SOURCE_PHOTOMETRY";
const FETCH_SOURCE_PHOTOMETRY_OK = "skyportal/FETCH_SOURCE_PHOTOMETRY_OK";
const FETCH_FILTER_WAVELENGTHS = "skyportal/FETCH_FILTER_WAVELENGTHS";
const FETCH_ALL_ORIGINS = "skyportal/FETCH_ALL_ORIGINS";
const FETCH_ALL_ORIGINS_OK = "skyportal/FETCH_ALL_ORIGINS_OK";

const REFRESH_SOURCE_PHOTOMETRY = "skyportal/REFRESH_SOURCE_PHOTOMETRY";

const DELETE_PHOTOMETRY = "skyportal/DELETE_PHOTOMETRY";

const SUBMIT_PHOTOMETRY = "skyportal/SUBMIT_PHOTOMETRY";

const UPDATE_PHOTOMETRY = "skyportal/UPDATE_PHOTOMETRY";

// eslint-disable-next-line import/prefer-default-export
export function fetchSourcePhotometry(id, params = {}) {
  return API.GET(`/api/sources/${id}/photometry`, FETCH_SOURCE_PHOTOMETRY, {
    includeOwnerInfo: true,
    includeStreamInfo: true,
    includeValidationInfo: true,
    ...params,
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
  return API.POST(
    "/api/photometry?refresh=true",
    SUBMIT_PHOTOMETRY,
    photometry,
  );
}

export function updatePhotometry(id, photometry) {
  return API.PATCH(
    `/api/photometry/${id}?refresh=true`,
    UPDATE_PHOTOMETRY,
    photometry,
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_SOURCE_PHOTOMETRY) {
    // check if the source photometry is already in the store
    // or if the source that is loaded is the one that is being
    // specified in the payload's obj_id
    const { source } = getState();
    const { obj_id, magsys } = payload;
    if (source?.id && source.id === obj_id) {
      dispatch(
        fetchSourcePhotometry(payload.obj_id, { magsys: magsys || "ab" }),
      );
    }
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
