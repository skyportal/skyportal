import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_EARTHQUAKE_STATUSES = "skyportal/FETCH_EARTHQUAKE_STATUSES";
const FETCH_EARTHQUAKE_STATUSES_OK = "skyportal/FETCH_EARTHQUAKE_STATUSES_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchEarthquakeStatuses = (filterParams = {}) =>
  API.GET("/api/earthquake/status", FETCH_EARTHQUAKE_STATUSES, filterParams);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_EARTHQUAKE_STATUSES) {
    dispatch(fetchEarthquakeStatuses());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_EARTHQUAKE_STATUSES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("earthquakeStatuses", reducer);
