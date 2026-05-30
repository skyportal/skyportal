import * as API from "../API";
import store from "../store";

const FETCH_ROLES = "skyportal/FETCH_ROLES";
const FETCH_ROLES_OK = "skyportal/FETCH_ROLES_OK";

const ADD_USER_ROLES = "skyportal/ADD_USER_ROLES";

const DELETE_USER_ROLE = "skyportal/DELETE_USER_ROLE";

export const fetchRoles = () => API.GET("/api/roles", FETCH_ROLES);

export const addUserRoles = ({
  userID,
  roleIds,
}: {
  userID: number | string;
  roleIds: any;
}) => API.POST(`/api/user/${userID}/roles`, ADD_USER_ROLES, { roleIds });

export const deleteUserRole = ({
  userID,
  role,
}: {
  userID: number | string;
  role: any;
}) => API.DELETE(`/api/user/${userID}/roles/${role}`, DELETE_USER_ROLE);

interface RolesAction {
  type: string;
  data?: any;
  [key: string]: any;
}

function reducer(state: any = null, action: RolesAction) {
  switch (action.type) {
    case FETCH_ROLES_OK: {
      return action.data;
    }
    default:
      return state;
  }
}

store.injectReducer("roles", reducer);
