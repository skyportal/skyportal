import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import store from "../store";

const FETCH_FOLLOWUP_REQUESTS = "skyportal/FETCH_FOLLOWUP_REQUESTS";
const FETCH_FOLLOWUP_REQUESTS_OK = "skyportal/FETCH_FOLLOWUP_REQUESTS_OK";

const PRIORITIZE_FOLLOWUP_REQUESTS = "skyportal/FETCH_FOLLOWUP_REQUESTS";

const REFRESH_FOLLOWUP_REQUESTS = "skyportal/REFRESH_FOLLOWUP_REQUESTS";

const ADD_TO_WATCH_LIST = "skyportal/ADD_TO_WATCH_LIST";
const REMOVE_FROM_WATCH_LIST = "skyportal/REMOVE_FROM_WATCH_LIST";

export const UPDATE_FOLLOWUP_FETCH_PARAMS =
  "skyportal/UPDATE_FOLLOWUP_FETCH_PARAMS";

export const addToWatchList = (id, params = {}) =>
  API.POST(`/api/followup_request/watch/${id}`, ADD_TO_WATCH_LIST, params);

export const removeFromWatchList = (id, params = {}) =>
  API.DELETE(
    `/api/followup_request/watch/${id}`,
    REMOVE_FROM_WATCH_LIST,
    params,
  );

export function fetchFollowupRequests(params = {}) {
  if (!Object.keys(params).includes("numPerPage")) {
    params.numPerPage = 10;
  }
  if (params?.noRedux === true) {
    return API.GET(
      "/api/followup_request",
      "skyportal/FETCH_FOLLOWUP_REQUESTS_NO_REDUX",
      params,
    );
  }
  return API.GET("/api/followup_request", FETCH_FOLLOWUP_REQUESTS, params);
}

// eslint-disable-next-line import/prefer-default-export
export const prioritizeFollowupRequests = (params = {}) =>
  API.PUT(
    "/api/followup_request/prioritization",
    PRIORITIZE_FOLLOWUP_REQUESTS,
    params,
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_FOLLOWUP_REQUESTS) {
    const params = store.getState().followup_requests.fetchingParams;
    dispatch(fetchFollowupRequests(params));
  }
});

const reducer = (
  state = { followupRequestList: [], totalMatches: 0 },
  action,
) => {
  switch (action.type) {
    case FETCH_FOLLOWUP_REQUESTS_OK: {
      const { followup_requests, totalMatches } = action.data;
      return {
        ...state,
        followupRequestList: followup_requests,
        totalMatches,
      };
    }
    case UPDATE_FOLLOWUP_FETCH_PARAMS: {
      const { data } = action;
      return {
        ...state,
        fetchingParams: data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("followup_requests", reducer);
