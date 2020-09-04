import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_RECENT_SOURCES = "skyportal/FETCH_RECENT_SOURCES";
export const FETCH_RECENT_SOURCES_OK = "skyportal/FETCH_RECENT_SOURCES_OK";

export const fetchRecentSources = () =>
  API.GET("/api/internal/recent_sources", FETCH_RECENT_SOURCES);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_RECENT_SOURCES) {
    dispatch(fetchRecentSources());
  }
});

const reducer = (state = { recentSources: undefined }, action) => {
  switch (action.type) {
    case FETCH_RECENT_SOURCES_OK: {
      const recentSources = action.data;
      return {
        recentSources,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("recentSources", reducer);
