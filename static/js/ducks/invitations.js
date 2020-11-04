import store from "../store";
import * as API from "../API";

export const INVITE_USER = "skyportal/INVITE_USER";
export const INVITE_USER_OK = "skyportal/INVITE_USER_OK";

export const FETCH_INVITATIONS = "skyportal/FETCH_INVITATIONS";
export const FETCH_INVITATIONS_OK = "skyportal/FETCH_INVITATIONS_OK";

export const inviteUser = ({ userEmail, streamIDs, groupIDs, groupAdmin }) =>
  API.POST("/api/invitations", INVITE_USER, {
    userEmail,
    streamIDs,
    groupIDs,
    groupAdmin,
  });

export const fetchInvitations = () =>
  API.GET("/api/invitations", FETCH_INVITATIONS);

function reducer(state = null, action) {
  switch (action.type) {
    case FETCH_INVITATIONS_OK: {
      return action.data;
    }
    default:
      return state;
  }
}

store.injectReducer("invitations", reducer);
