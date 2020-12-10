import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SOURCE_COUNTS = "skyportal/FETCH_SOURCE_COUNTS";
const FETCH_SOURCE_COUNTS_OK = "skyportal/FETCH_SOURCE_COUNTS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchSourceCounts = () =>
  API.GET("/api/internal/source_counts", FETCH_SOURCE_COUNTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_SOURCE_COUNTS) {
    dispatch(fetchSourceCounts());
  }
});

const reducer = (state = null, action) => {
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
