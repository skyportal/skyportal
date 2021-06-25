import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_GCNEVENTS = "skyportal/FETCH_GCNEVENTS";
export const FETCH_GCNEVENTS_OK = "skyportal/FETCH_GCNEVENTS_OK";

export const fetchGcnEvents = () => API.GET("/api/gcn_event", FETCH_GCNEVENTS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_GCNEVENTS) {
    dispatch(fetchGcnEvents());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GCNEVENTS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("gcnEvents", reducer);
