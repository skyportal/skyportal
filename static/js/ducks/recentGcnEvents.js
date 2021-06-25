import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_GCNEVENTS = "skyportal/FETCH_GCNEVENTS";
export const FETCH_RECENT_GCNEVENTS_OK = "skyportal/FETCH_RECENT_GCNEVENTS_OK";

export const fetchGcnEvents = () =>
  API.GET("/api/gcn_event", FETCH_RECENT_GCNEVENTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_RECENT_GCNEVENTS) {
    dispatch(fetchRecentGcnEvents());
  }
});

const reducer = (state = { gcnEvents: [] }, action) => {
  switch (action.type) {
    case FETCH_RECENT_GCNEVENTS_OK: {
      const gcnEvents = action.data;
      return {
        gcnEvents,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("recentGcnEvents", reducer);
