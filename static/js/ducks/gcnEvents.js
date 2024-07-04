import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_GCN_EVENTS = "skyportal/REFRESH_GCN_EVENTS";

const FETCH_GCN_EVENTS = "skyportal/FETCH_GCN_EVENTS";
const FETCH_GCN_EVENTS_OK = "skyportal/FETCH_GCN_EVENTS_OK";

const ADD_GCN_EVENT_USER = "skyportal/ADD_GCN_EVENT_USER";

const DELETE_GCN_EVENT_USER = "skyportal/DELETE_GCN_EVENT_USER";

export const fetchGcnEvents = (filterParams = {}) =>
  API.GET("/api/gcn_event", FETCH_GCN_EVENTS, filterParams);

export function addGcnEventUser(userID, gcnEventDateobs) {
  return API.POST(
    `/api/gcn_event/${gcnEventDateobs}/users`,
    ADD_GCN_EVENT_USER,
    {
      userID,
    },
  );
}

export function deleteGcnEventUser(userID, gcnEventDateobs) {
  return API.DELETE(
    `/api/gcn_event/${gcnEventDateobs}/users/${userID}`,
    DELETE_GCN_EVENT_USER,
    { userID, gcnEventDateobs },
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_GCN_EVENTS) {
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
