import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import store from "../store";

const FETCH_TAG_OPTIONS = "skyportal/FETCH_TAG_OPTIONS";
const FETCH_TAG_OPTIONS_OK = "skyportal/FETCH_TAG_OPTIONS_OK";

const CREATE_TAG_OPTION = "skyportal/CREATE_TAG_OPTION";
const CREATE_TAG_OPTION_OK = "skyportal/CREATE_TAG_OPTION_OK";

const UPDATE_TAG_OPTION = "skyportal/UPDATE_TAG_OPTION";
const DELETE_TAG_OPTION = "skyportal/DELETE_TAG_OPTION";

const ADD_OBJECT_TAG = "skyportal/ADD_OBJECT_TAG";

const DELETE_OBJECT_TAG = "skyportal/DELETE_OBJECT_TAG";

export function fetchTagOptions() {
  return API.GET("/api/objtagoption", FETCH_TAG_OPTIONS);
}

export function createTagOption(data: any) {
  return API.POST("/api/objtagoption", CREATE_TAG_OPTION, data);
}

export function updateTagOption(data: any) {
  return API.PATCH(`/api/objtagoption/${data.id}`, UPDATE_TAG_OPTION, data);
}

export function deleteTagOption(data: any) {
  return API.DELETE(`/api/objtagoption/${data.id}`, DELETE_TAG_OPTION, data);
}

export function addObjectTag(data: any) {
  return API.POST("/api/objtag", ADD_OBJECT_TAG, data);
}

export function deleteObjectTag(data: any) {
  return API.DELETE(`/api/objtag/${data.id}`, DELETE_OBJECT_TAG, data);
}

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_TAG_OPTIONS) {
    dispatch(fetchTagOptions());
  }
});

interface ObjectTagsAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (state: any[] = [], action: ObjectTagsAction): any[] => {
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
