import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_TOP_GCNEVENTS = "skyportal/FETCH_TOP_GCNEVENTS";
export const FETCH_TOP_GCNEVENTS_OK = "skyportal/FETCH_TOP_GCNEVENTS_OK";

export const fetchTopGcnEvents = () =>
  API.GET("/api/gcn/event_views", FETCH_TOP_GCNEVENTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_TOP_GCNEVENTS) {
    dispatch(fetchTopGcnEvents());
  }
});

const reducer = (state = { gcnEvents: [] }, action) => {
  switch (action.type) {
    case FETCH_TOP_GCNEVENTS_OK: {
      const gcnEvents = action.data;
      return {
        gcnEvents,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("topGcnEvents", reducer);
