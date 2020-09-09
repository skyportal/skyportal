import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_SOURCE_COUNTS = "skyportal/FETCH_SOURCE_COUNTS";
export const FETCH_SOURCE_COUNTS_OK = "skyportal/FETCH_SOURCE_COUNTS_OK";

export const fetchSourceCounts = () =>
  API.GET("/api/internal/source_counts", FETCH_SOURCE_COUNTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_SOURCE_COUNTS) {
    dispatch(fetchSourceCounts());
  }
});

const reducer = (state = { sourceViews: [] }, action) => {
  switch (action.type) {
    case FETCH_SOURCE_COUNTS_OK: {
      const sourceCounts = action.data;
      return {
        sourceCounts,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sourceCounts", reducer);
