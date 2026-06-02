import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_USERS_MANAGEMENT = "skyportal/FETCH_USERS_MANAGEMENT";
const FETCH_USERS_MANAGEMENT_OK = "skyportal/FETCH_USERS_MANAGEMENT_OK";
const SET_USERS_MANAGEMENT_FETCH_PARAMS =
  "skyportal/SET_USERS_MANAGEMENT_FETCH_PARAMS";

// let's expose a function to set the fetchParams in the redux store
export function setUsersManagementFetchParams(fetchParams: any) {
  return {
    type: SET_USERS_MANAGEMENT_FETCH_PARAMS,
    fetchParams,
  };
}

export function fetchUsersManagement() {
  const state = store.getState();
  const filterParams = {
    pageNumber: 1,
    numPerPage: 25,
    ...state.users_management.fetchParams,
  };
  return API.GET("/api/user", FETCH_USERS_MANAGEMENT, filterParams);
}

// Websocket message handler
messageHandler.add(
  (actionType: string, _payload: any, dispatch: AppDispatch) => {
    if (actionType === FETCH_USERS_MANAGEMENT) {
      dispatch(fetchUsersManagement());
    }
  },
);

type UsersManagementState = Record<string, any>;

interface UsersManagementAction {
  type: string;
  data?: any;
  fetchParams?: any;
}

const reducer = (
  state: UsersManagementState = { users: [], fetchParams: {}, totalMatches: 0 },
  action: UsersManagementAction,
): UsersManagementState => {
  switch (action.type) {
    case FETCH_USERS_MANAGEMENT_OK: {
      const { users, totalMatches } = action.data;
      return {
        ...state,
        users,
        totalMatches,
      };
    }
    case SET_USERS_MANAGEMENT_FETCH_PARAMS: {
      return {
        ...state,
        fetchParams: action.fetchParams,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("users_management", reducer);
