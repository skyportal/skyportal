import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_GCN_PROPERTIES = "skyportal/FETCH_GCN_PROPERTIES";
const FETCH_GCN_PROPERTIES_OK = "skyportal/FETCH_GCN_PROPERTIES_OK";

export const fetchGcnProperties = (filterParams = {}) =>
  API.GET("/api/gcn_event/properties", FETCH_GCN_PROPERTIES, filterParams);

// Websocket message handler
messageHandler.add(
  (actionType: string, _payload: any, dispatch: AppDispatch) => {
    if (actionType === FETCH_GCN_PROPERTIES) {
      dispatch(fetchGcnProperties());
    }
  },
);

type GcnPropertiesState = any;

interface GcnPropertiesAction {
  type: string;
  data?: any;
}

const reducer = (
  state: GcnPropertiesState = null,
  action: GcnPropertiesAction,
): GcnPropertiesState => {
  switch (action.type) {
    case FETCH_GCN_PROPERTIES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("gcnProperties", reducer);
