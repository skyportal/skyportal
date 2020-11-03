import * as API from "../API";

export const INVITE_USER = "skyportal/INVITE_USER";
export const INVITE_USER_OK = "skyportal/INVITE_USER_OK";

export const inviteUser = ({ userEmail, streamIDs, groupIDs, groupAdmin }) =>
  API.POST("/api/invitations", INVITE_USER, {
    userEmail,
    streamIDs,
    groupIDs,
    groupAdmin,
  });
