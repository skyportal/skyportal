import store from "../store";
import * as API from "../API";

export const INVITE_USER = "skyportal/INVITE_USER";
export const INVITE_USER_OK = "skyportal/INVITE_USER_OK";

export const FETCH_INVITATIONS = "skyportal/FETCH_INVITATIONS";
export const FETCH_INVITATIONS_OK = "skyportal/FETCH_INVITATIONS_OK";

export const UPDATE_INVITATION = "skyportal/UPDATE_INVITATION";

export const DELETE_INVITATION = "skyportal/DELETE_INVITATION";

export const inviteUser = ({ userEmail, streamIDs, groupIDs, groupAdmin }) =>
  API.POST("/api/invitations", INVITE_USER, {
    userEmail,
    streamIDs,
    groupIDs,
    groupAdmin,
  });

export const fetchInvitations = () =>
  API.GET("/api/invitations", FETCH_INVITATIONS);

export const updateInvitation = (invitationID, payload) =>
  API.PATCH(`/api/invitations/${invitationID}`, UPDATE_INVITATION, payload);

export const deleteInvitation = (invitationID) =>
  API.DELETE(`/api/invitations/${invitationID}`, DELETE_INVITATION);

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
