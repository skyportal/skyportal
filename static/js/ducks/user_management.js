import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_USERS_MANAGEMENT = "skyportal/FETCH_USERS";
const FETCH_USERS_MANAGEMENT_OK = "skyportal/FETCH_USERS_OK";

export function fetchUsersManagement(filterParams = {}) {
  return API.GET("/api/user", FETCH_USERS_MANAGEMENT, filterParams);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_USERS_MANAGEMENT) {
    dispatch(fetchUsersManagement());
  }
});

const reducer = (state = { users: [], totalMatches: 0 }, action) => {
  switch (action.type) {
    case FETCH_USERS_MANAGEMENT_OK: {
      const { users, totalMatches } = action.data;
      return {
        ...state,
        users,
        totalMatches,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("users_management", reducer);
