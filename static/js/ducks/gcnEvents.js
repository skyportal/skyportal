import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GCN_EVENTS = "skyportal/FETCH_GCN_EVENTS";
const FETCH_GCN_EVENTS_OK = "skyportal/FETCH_GCN_EVENTS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchGcnEvents = () => API.GET("/api/gcn_event", FETCH_GCN_EVENTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_GCN_EVENTS) {
    dispatch(fetchGcnEvents());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GCN_EVENTS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("gcnEvents", reducer);
