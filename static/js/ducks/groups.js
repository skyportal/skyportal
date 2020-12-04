import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_GROUPS = "skyportal/FETCH_GROUPS";
export const FETCH_GROUPS_OK = "skyportal/FETCH_GROUPS_OK";

export const ADD_GROUP = "skyportal/ADD_GROUP";
export const ADD_GROUP_OK = "skyportal/ADD_GROUP_OK";

export const DELETE_GROUP = "skyportal/DELETE_GROUP";
export const DELETE_GROUP_OK = "skyportal/DELETE_GROUP_OK";

export const ADD_GROUP_USER = "skyportal/ADD_GROUP_USER";
export const ADD_GROUP_USER_OK = "skyportal/ADD_GROUP_USER_OK";

export const REQUEST_GROUP_ADMISSION = "skyportal/REQUEST_GROUP_ADMISSION";
export const REQUEST_GROUP_ADMISSION_OK =
  "skyportal/REQUEST_GROUP_ADMISSION_OK";

const DELETE_GROUP_ADMISSION_REQUEST =
  "skyportal/DELETE_GROUP_ADMISSION_REQUEST";

export const ADD_GROUP_USERS = "skyportal/ADD_GROUP_USERS";
export const ADD_GROUP_USERS_OK = "skyportal/ADD_GROUP_USERS_OK";

export const UPDATE_GROUP_USER = "skyportal/UPDATE_GROUP_USER";
export const UPDATE_GROUP_USER_OK = "skyportal/UPDATE_GROUP_USER_OK";

export const DELETE_GROUP_USER = "skyportal/DELETE_GROUP_USER";
export const DELETE_GROUP_USER_OK = "skyportal/DELETE_GROUP_USER_OK";

export function fetchGroups(includeSingleUserGroups = false) {
  return API.GET(
    `/api/groups?includeSingleUserGroups=${includeSingleUserGroups}`,
    FETCH_GROUPS
  );
}

export const requestGroupAdmission = (userID, groupID) =>
  API.POST("/api/group_admission_requests", REQUEST_GROUP_ADMISSION, {
    userID,
    groupID,
  });

export const deleteAdmissionRequest = (ID) =>
  API.DELETE(
    `/api/group_admission_requests/${ID}`,
    DELETE_GROUP_ADMISSION_REQUEST
  );

export function addNewGroup(form_data) {
  return API.POST("/api/groups", ADD_GROUP, form_data);
}

export function deleteGroup(group_id) {
  return API.DELETE(`/api/groups/${group_id}`, DELETE_GROUP);
}

export function addGroupUser({ userID, admin, group_id }) {
  return API.POST(`/api/groups/${group_id}/users`, ADD_GROUP_USER, {
    userID,
    admin,
    group_id,
  });
}

export const addAllUsersFromGroups = ({ toGroupID, fromGroupIDs }) =>
  API.POST(`/api/groups/${toGroupID}/usersFromGroups`, ADD_GROUP_USERS, {
    fromGroupIDs,
  });

export const updateGroupUser = (groupID, params) =>
  API.PATCH(`/api/groups/${groupID}/users`, UPDATE_GROUP_USER, params);

export function deleteGroupUser({ userID, group_id }) {
  return API.DELETE(
    `/api/groups/${group_id}/users/${userID}`,
    DELETE_GROUP_USER,
    { userID, group_id }
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_GROUPS) {
    dispatch(fetchGroups(true));
  }
});

function reducer(state = { user: [], userAccessible: [], all: null }, action) {
  switch (action.type) {
    case FETCH_GROUPS_OK: {
      const { user_groups, user_accessible_groups, all_groups } = action.data;
      return {
        ...state,
        user: user_groups,
        userAccessible: user_accessible_groups,
        all: all_groups,
      };
    }
    default:
      return state;
  }
}

store.injectReducer("groups", reducer);
