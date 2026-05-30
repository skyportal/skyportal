import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

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

export function deleteDefaultFollowupRequest(id: number | string) {
  return API.DELETE(
    `/api/default_followup_request/${id}`,
    DELETE_DEFAULT_FOLLOWUP_REQUEST,
  );
}

export const fetchDefaultFollowupRequests = () =>
  API.GET("/api/default_followup_request", FETCH_DEFAULT_FOLLOWUP_REQUESTS);

export const submitDefaultFollowupRequest = (default_plan: any) =>
  API.POST(
    `/api/default_followup_request`,
    SUBMIT_DEFAULT_FOLLOWUP_REQUEST,
    default_plan,
  );

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === REFRESH_DEFAULT_FOLLOWUP_REQUESTS) {
      dispatch(fetchDefaultFollowupRequests());
    }
  },
);

type DefaultFollowupRequestsState = Record<string, any>;

interface DefaultFollowupRequestsAction {
  type: string;
  data?: any;
}

const reducer = (
  state: DefaultFollowupRequestsState = {
    defaultFollowupRequestList: [],
  },
  action: DefaultFollowupRequestsAction,
): DefaultFollowupRequestsState => {
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
