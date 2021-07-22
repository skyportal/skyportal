import store from "../store";
import * as API from "../API";

const INVITE_USER = "skyportal/INVITE_USER";

const FETCH_INVITATIONS = "skyportal/FETCH_INVITATIONS";
const FETCH_INVITATIONS_OK = "skyportal/FETCH_INVITATIONS_OK";

const UPDATE_INVITATION = "skyportal/UPDATE_INVITATION";

const DELETE_INVITATION = "skyportal/DELETE_INVITATION";

export const inviteUser = (data) =>
  API.POST("/api/invitations", INVITE_USER, data);

export const fetchInvitations = (filterParams = {}) => {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  return API.GET("/api/invitations", FETCH_INVITATIONS, filterParams);
};

export const updateInvitation = (invitationID, payload) =>
  API.PATCH(`/api/invitations/${invitationID}`, UPDATE_INVITATION, payload);

export const deleteInvitation = (invitationID) =>
  API.DELETE(`/api/invitations/${invitationID}`, DELETE_INVITATION);

function reducer(state = { invitations: [], totalMatches: 0 }, action) {
  switch (action.type) {
    case FETCH_INVITATIONS_OK: {
      const { invitations, totalMatches } = action.data;
      return {
        ...state,
        invitations,
        totalMatches,
      };
    }
    default:
      return state;
  }
}

store.injectReducer("invitations", reducer);
