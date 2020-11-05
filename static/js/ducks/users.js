import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_USER = "skyportal/FETCH_USER";
export const FETCH_USER_OK = "skyportal/FETCH_USER_OK";

export const FETCH_USERS = "skyportal/FETCH_USERS";
export const FETCH_USERS_OK = "skyportal/FETCH_USERS_OK";

export function fetchUser(id) {
  return API.GET(`/api/user/${id}`, FETCH_USER);
}

export function fetchUsers(filterParams = {}) {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/user?${queryString}`, FETCH_USERS);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_USERS) {
    dispatch(fetchUsers());
  }
});

const reducer = (state = { users: [], totalMatches: 0 }, action) => {
  switch (action.type) {
    case FETCH_USER_OK: {
      const { id, ...userInfo } = action.data;
      return {
        ...state,
        [id]: userInfo,
      };
    }
    case FETCH_USERS_OK: {
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

store.injectReducer("users", reducer);
