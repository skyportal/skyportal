import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import { showNotification } from "baselayer/components/Notifications";
import store from "../store";

const FETCH_TAG_OPTIONS = "skyportal/FETCH_TAG_OPTIONS";
const FETCH_TAG_OPTIONS_OK = "skyportal/FETCH_TAG_OPTIONS_OK";

const ADD_OBJECT_TAG = "skyportal/ADD_OBJECT_TAG";
const ADD_OBJECT_TAG_OK = "skyportal/ADD_OBJECT_TAG_OK";
const ADD_OBJECT_TAG_ERROR = "skyportal/ADD_OBJECT_TAG_ERROR";

const DELETE_OBJECT_TAG = "skyportal/DELETE_OBJECT_TAG";
const DELETE_OBJECT_TAG_OK = "skyportal/DELETE_OBJECT_TAG_OK";
const DELETE_OBJECT_TAG_ERROR = "skyportal/DELETE_OBJECT_TAG_ERROR";

export function fetchTagOptions() {
  return API.GET("/api/objtagoption", FETCH_TAG_OPTIONS);
}

export function addObjectTag(data) {
  return API.POST("/api/objtag", ADD_OBJECT_TAG, data);
}

export function deleteObjectTag(data) {
  return API.DELETE("/api/objtag", DELETE_OBJECT_TAG, data);
}

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === "skyportal/REFRESH_OBJECT_TAGS") {
    const objectId = payload?.objectId;
    if (objectId) {
      dispatch(fetchObjectTags(objectId));
    }
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_TAG_OPTIONS_OK: {
      return action.data || [];
    }
    default:
      return state;
  }
};

store.injectReducer("objectTags", reducer);
