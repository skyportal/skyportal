import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SOURCE_COUNTS = "skyportal/FETCH_SOURCE_COUNTS";
const FETCH_SOURCE_COUNTS_OK = "skyportal/FETCH_SOURCE_COUNTS_OK";

export const fetchSourceCounts = () =>
  API.GET("/api/internal/source_counts", FETCH_SOURCE_COUNTS);

// Websocket message handler
messageHandler.add((actionType: any, payload: any, dispatch: any) => {
  if (actionType === FETCH_SOURCE_COUNTS) {
    dispatch(fetchSourceCounts());
  }
});

interface SourceCountsAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> | null = null,
  action: SourceCountsAction,
): Record<string, any> | null => {
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
