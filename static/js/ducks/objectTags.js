import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import { showNotification } from "baselayer/components/Notifications";
import store from "../store";

const FETCH_TAG_OPTIONS = "skyportal/FETCH_TAG_OPTIONS";
const FETCH_TAG_OPTIONS_OK = "skyportal/FETCH_TAG_OPTIONS_OK";

const CREATE_TAG_OPTION = "skyportal/CREATE_TAG_OPTION";
const CREATE_TAG_OPTION_OK = "skyportal/CREATE_TAG_OPTION_OK";

const ADD_OBJECT_TAG = "skyportal/ADD_OBJECT_TAG";

const DELETE_OBJECT_TAG = "skyportal/DELETE_OBJECT_TAG";

export function fetchTagOptions() {
  return API.GET("/api/objtagoption", FETCH_TAG_OPTIONS);
}

export function createTagOption(data) {
  return API.POST("/api/objtagoption", CREATE_TAG_OPTION, data);
}

export function addObjectTag(data) {
  return API.POST("/api/objtag", ADD_OBJECT_TAG, data);
}

export function deleteObjectTag(data) {
  return API.DELETE(`/api/objtag/${data.id}`, DELETE_OBJECT_TAG, data);
}

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_TAG_OPTIONS_OK: {
      return action.data || [];
    }
    case CREATE_TAG_OPTION_OK: {
      return [...state, action.data];
    }
    default:
      return state;
  }
};

store.injectReducer("objectTags", reducer);
