import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_EARTHQUAKE_STATUSES = "skyportal/FETCH_EARTHQUAKE_STATUSES";
const FETCH_EARTHQUAKE_STATUSES_OK = "skyportal/FETCH_EARTHQUAKE_STATUSES_OK";

export const fetchEarthquakeStatuses = (filterParams = {}) =>
  API.GET("/api/earthquake/status", FETCH_EARTHQUAKE_STATUSES, filterParams);

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === FETCH_EARTHQUAKE_STATUSES) {
      dispatch(fetchEarthquakeStatuses());
    }
  },
);

type EarthquakeStatusesState = any;

interface EarthquakeStatusesAction {
  type: string;
  data?: any;
}

const reducer = (
  state: EarthquakeStatusesState = null,
  action: EarthquakeStatusesAction,
): EarthquakeStatusesState => {
  switch (action.type) {
    case FETCH_EARTHQUAKE_STATUSES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("earthquakeStatuses", reducer);
