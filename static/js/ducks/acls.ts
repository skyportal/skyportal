import * as API from "../API";
import store from "../store";

const FETCH_ACLS = "skyportal/FETCH_ACLS";
const FETCH_ACLS_OK = "skyportal/FETCH_ACLS_OK";

const ADD_USER_ACLS = "skyportal/ADD_USER_ACLS";

const DELETE_USER_ACL = "skyportal/DELETE_USER_ACL";

export const fetchACLs = () => API.GET("/api/acls", FETCH_ACLS);

export const addUserACLs = ({
  userID,
  aclIds,
}: {
  userID: number | string;
  aclIds: string[];
}) => API.POST(`/api/user/${userID}/acls`, ADD_USER_ACLS, { aclIds });

export const deleteUserACL = ({
  userID,
  acl,
}: {
  userID: number | string;
  acl: string;
}) => API.DELETE(`/api/user/${userID}/acls/${acl}`, DELETE_USER_ACL);

function reducer(state: any = null, action: { type: string; data?: any }): any {
  switch (action.type) {
    case FETCH_ACLS_OK: {
      return action.data;
    }
    default:
      return state;
  }
}

store.injectReducer("acls", reducer);
