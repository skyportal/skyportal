import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_FOLLOWUP_REQUESTS = "skyportal/FETCH_FOLLOWUP_REQUESTS";
const FETCH_FOLLOWUP_REQUESTS_OK = "skyportal/FETCH_FOLLOWUP_REQUESTS_OK";

const REFRESH_FOLLOWUP_REQUESTS = "skyportal/REFRESH_FOLLOWUP_REQUESTS";

// eslint-disable-next-line import/prefer-default-export
export const fetchFollowupRequests = (params = {}) =>
  API.GET("/api/followup_request", FETCH_FOLLOWUP_REQUESTS, params);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_FOLLOWUP_REQUESTS) {
    dispatch(fetchFollowupRequests());
  }
});

const reducer = (state = { followupRequestList: [] }, action) => {
  switch (action.type) {
    case FETCH_FOLLOWUP_REQUESTS_OK: {
      const followupRequestList = action.data;
      return {
        ...state,
        followupRequestList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("followup_requests", reducer);
