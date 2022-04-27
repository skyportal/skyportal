import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_FOLLOWUP_REQUESTS = "skyportal/FETCH_FOLLOWUP_REQUESTS";
const FETCH_FOLLOWUP_REQUESTS_OK = "skyportal/FETCH_FOLLOWUP_REQUESTS_OK";

const REFRESH_FOLLOWUP_REQUESTS = "skyportal/REFRESH_FOLLOWUP_REQUESTS";

const PRIORITIZE_FOLLOWUP_REQUESTS = "skyportal/FETCH_FOLLOWUP_REQUESTS";

export function fetchFollowupRequests(params = {}) {
  if (!Object.keys(params).includes("pageNumber")) {
    params.pageNumber = 1;
  }
  if (!Object.keys(params).includes("numPerPage")) {
    params.numPerPage = 10;
  }
  return API.GET("/api/followup_request", FETCH_FOLLOWUP_REQUESTS, params);
}

// eslint-disable-next-line import/prefer-default-export
export const prioritizeFollowupRequests = (params = {}) =>
  API.PUT(
    "/api/followup_request/prioritization",
    PRIORITIZE_FOLLOWUP_REQUESTS,
    params
  );

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_FOLLOWUP_REQUESTS) {
    dispatch(fetchFollowupRequests());
  }
});

const reducer = (
  state = { followupRequestList: [], totalMatches: 0 },
  action
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
    default:
      return state;
  }
};

store.injectReducer("followup_requests", reducer);
