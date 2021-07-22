import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_RECENT_GCNEVENTS = "skyportal/FETCH_RECENT_GCNEVENTS";
const FETCH_RECENT_GCNEVENTS_OK = "skyportal/FETCH_RECENT_GCNEVENTS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchRecentGcnEvents = () =>
  API.GET("/api/internal/recent_gcn_events", FETCH_RECENT_GCNEVENTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_RECENT_GCNEVENTS) {
    dispatch(fetchRecentGcnEvents());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_RECENT_GCNEVENTS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("recentGcnEvents", reducer);
