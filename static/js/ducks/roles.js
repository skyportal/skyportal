import * as API from "../API";
import store from "../store";

export const FETCH_ROLES = "skyportal/FETCH_ROLES";
export const FETCH_ROLES_OK = "skyportal/FETCH_ROLES_OK";

export const ADD_USER_ROLES = "skyportal/ADD_USER_ROLES";

export const DELETE_USER_ROLE = "skyportal/DELETE_USER_ROLE";

export const fetchRoles = () => API.GET("/api/roles", FETCH_ROLES);

export const addUserRoles = ({ userID, roleIds }) =>
  API.POST(`/api/user/${userID}/roles`, ADD_USER_ROLES, { roleIds });

export const deleteUserRole = ({ userID, role }) =>
  API.DELETE(`/api/user/${userID}/roles/${role}`, DELETE_USER_ROLE);

function reducer(state = null, action) {
  switch (action.type) {
    case FETCH_ROLES_OK: {
      return action.data;
    }
    default:
      return state;
  }
}

store.injectReducer("roles", reducer);
