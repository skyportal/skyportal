import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_USER = "skyportal/FETCH_USER";
const FETCH_USER_OK = "skyportal/FETCH_USER_OK";

const FETCH_USERS = "skyportal/FETCH_USERS";
const FETCH_USERS_OK = "skyportal/FETCH_USERS_OK";

const PATCH_USER = "skyportal/PATCH_USER";

export function fetchUser(id) {
  return API.GET(`/api/user/${id}`, FETCH_USER);
}

export function fetchUsers(filterParams = {}) {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  return API.GET("/api/user", FETCH_USERS, filterParams);
}

export function patchUser(id, data) {
  return API.PATCH(`/api/user/${id}`, PATCH_USER, data);
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
        users: {
          [id]: userInfo,
        },
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
