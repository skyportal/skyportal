import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_TOP_SOURCES = "skyportal/FETCH_TOP_SOURCES";
const FETCH_TOP_SOURCES_OK = "skyportal/FETCH_TOP_SOURCES_OK";

export const fetchTopSources = () =>
  API.GET("/api/internal/source_views", FETCH_TOP_SOURCES);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_TOP_SOURCES) {
    dispatch(fetchTopSources());
  }
});

interface TopSourcesState {
  sourceViews: any[];
}

interface TopSourcesAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: TopSourcesState = { sourceViews: [] },
  action: TopSourcesAction,
): TopSourcesState => {
  switch (action.type) {
    case FETCH_TOP_SOURCES_OK: {
      const sourceViews = action.data;
      return {
        sourceViews,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("topSources", reducer);
