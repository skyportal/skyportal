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

export function fetchUsers() {
  return API.GET("/api/user", FETCH_USERS);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_USERS) {
    dispatch(fetchUsers());
  }
});

const reducer = (state = { allUsers: [] }, action) => {
  switch (action.type) {
    case FETCH_USER_OK: {
      const { id, ...userInfo } = action.data;
      return {
        ...state,
        [id]: userInfo,
      };
    }
    case FETCH_USERS_OK: {
      const users = action.data;
      return {
        ...state,
        allUsers: users,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("users", reducer);
