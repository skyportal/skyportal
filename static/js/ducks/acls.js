import * as API from "../API";
import store from "../store";

export const FETCH_ACLS = "skyportal/FETCH_ACLS";
export const FETCH_ACLS_OK = "skyportal/FETCH_ACLS_OK";

export const ADD_USER_ACLS = "skyportal/ADD_USER_ACLS";

export const DELETE_USER_ACL = "skyportal/DELETE_USER_ACL";

export const fetchACLs = () => API.GET("/api/acls", FETCH_ACLS);

export const addUserACLs = ({ userID, aclIds }) =>
  API.POST(`/api/user/${userID}/acls`, ADD_USER_ACLS, { aclIds });

export const deleteUserACL = ({ userID, acl }) =>
  API.DELETE(`/api/user/${userID}/acls/${acl}`, DELETE_USER_ACL);

function reducer(state = null, action) {
  switch (action.type) {
    case FETCH_ACLS_OK: {
      return action.data;
    }
    default:
      return state;
  }
}

store.injectReducer("acls", reducer);
