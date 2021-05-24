import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GROUPS = "skyportal/FETCH_GROUPS";
const FETCH_GROUPS_OK = "skyportal/FETCH_GROUPS_OK";

const ADD_GROUP = "skyportal/ADD_GROUP";

const DELETE_GROUP = "skyportal/DELETE_GROUP";

const ADD_GROUP_USER = "skyportal/ADD_GROUP_USER";

const ADD_GROUP_USERS = "skyportal/ADD_GROUP_USERS";

const UPDATE_GROUP_USER = "skyportal/UPDATE_GROUP_USER";

const DELETE_GROUP_USER = "skyportal/DELETE_GROUP_USER";

export function fetchGroups(includeSingleUserGroups = false) {
  return API.GET(
    `/api/groups?includeSingleUserGroups=${includeSingleUserGroups}`,
    FETCH_GROUPS
  );
}

export function addNewGroup(form_data) {
  return API.POST("/api/groups", ADD_GROUP, form_data);
}

export function deleteGroup(group_id) {
  return API.DELETE(`/api/groups/${group_id}`, DELETE_GROUP);
}

export function addGroupUser({ userID, admin, group_id, canSave }) {
  return API.POST(`/api/groups/${group_id}/users`, ADD_GROUP_USER, {
    userID,
    admin,
    group_id,
    canSave,
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
