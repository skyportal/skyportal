import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_GROUP = "skyportal/REFRESH_GROUP";

const FETCH_GROUP = "skyportal/FETCH_GROUP";
const FETCH_GROUP_OK = "skyportal/FETCH_GROUP_OK";
const FETCH_GROUP_ERROR = "skyportal/FETCH_GROUP_ERROR";
const FETCH_GROUP_FAIL = "skyportal/FETCH_GROUP_FAIL";

// eslint-disable-next-line import/prefer-default-export
export function fetchGroup(id) {
  return API.GET(`/api/groups/${id}`, FETCH_GROUP);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { group } = getState();

  if (actionType === REFRESH_GROUP) {
    const loaded_group_id = group ? group.id : null;

    if (loaded_group_id === payload.group_id) {
      dispatch(fetchGroup(loaded_group_id));
    }
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GROUP_OK: {
      return action.data;
    }
    case FETCH_GROUP_FAIL:
    case FETCH_GROUP_ERROR: {
      return null;
    }
    default:
      return state;
  }
};

store.injectReducer("group", reducer);
