import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GCN_PROPERTIES = "skyportal/FETCH_GCN_PROPERTIES";
const FETCH_GCN_PROPERTIES_OK = "skyportal/FETCH_GCN_PROPERTIES_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchGcnProperties = (filterParams = {}) =>
  API.GET("/api/gcn_event/properties", FETCH_GCN_PROPERTIES, filterParams);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_GCN_PROPERTIES) {
    dispatch(fetchGcnProperties());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GCN_PROPERTIES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("gcnProperties", reducer);
