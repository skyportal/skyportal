import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_DEFAULT_FOLLOWUP_REQUESTS =
  "skyportal/REFRESH_DEFAULT_FOLLOWUP_REQUESTS";

const DELETE_DEFAULT_FOLLOWUP_REQUEST =
  "skyportal/DELETE_DEFAULT_FOLLOWUP_REQUEST";

const FETCH_DEFAULT_FOLLOWUP_REQUESTS =
  "skyportal/FETCH_DEFAULT_FOLLOWUP_REQUESTS";
const FETCH_DEFAULT_FOLLOWUP_REQUESTS_OK =
  "skyportal/FETCH_DEFAULT_FOLLOWUP_REQUESTS_OK";

const SUBMIT_DEFAULT_FOLLOWUP_REQUEST =
  "skyportal/SUBMIT_DEFAULT_FOLLOWUP_REQUEST";

export function deleteDefaultFollowupRequest(id) {
  return API.DELETE(
    `/api/default_followup_request/${id}`,
    DELETE_DEFAULT_FOLLOWUP_REQUEST,
  );
}

export const fetchDefaultFollowupRequests = () =>
  API.GET("/api/default_followup_request", FETCH_DEFAULT_FOLLOWUP_REQUESTS);

export const submitDefaultFollowupRequest = (default_plan) =>
  API.POST(
    `/api/default_followup_request`,
    SUBMIT_DEFAULT_FOLLOWUP_REQUEST,
    default_plan,
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_DEFAULT_FOLLOWUP_REQUESTS) {
    dispatch(fetchDefaultFollowupRequests());
  }
});

const reducer = (
  state = {
    defaultFollowupRequestList: [],
  },
  action,
) => {
  switch (action.type) {
    case FETCH_DEFAULT_FOLLOWUP_REQUESTS_OK: {
      const default_followup_requests = action.data;
      return {
        ...state,
        defaultFollowupRequestList: default_followup_requests,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("default_followup_requests", reducer);
