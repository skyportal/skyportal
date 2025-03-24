import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_FOLLOWUP_APIS = "FETCH_FOLLOWUP_APIS";
export const FETCH_FOLLOWUP_APIS_OK = "FETCH_FOLLOWUP_APIS_OK";

export const REFRESH_FOLLOWUP_APIS = "REFRESH_FOLLOWUP_APIS";

export const fetchFollowupApis = () =>
  API.GET("/api/internal/followup_apis", FETCH_FOLLOWUP_APIS, {});

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_FOLLOWUP_APIS) {
    dispatch(fetchFollowupApis());
  }
});

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_FOLLOWUP_APIS_OK: {
      const followupApis = action.data;
      return {
        ...state,
        followupApis,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("followupApis", reducer);
