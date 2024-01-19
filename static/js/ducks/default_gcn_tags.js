import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_DEFAULT_GCN_TAGS = "skyportal/REFRESH_DEFAULT_GCN_TAGS";

const DELETE_DEFAULT_GCN_TAG = "skyportal/DELETE_DEFAULT_GCN_TAG";

const FETCH_DEFAULT_GCN_TAGS = "skyportal/FETCH_DEFAULT_GCN_TAGS";
const FETCH_DEFAULT_GCN_TAGS_OK = "skyportal/FETCH_DEFAULT_GCN_TAGS_OK";

const SUBMIT_DEFAULT_GCN_TAG = "skyportal/SUBMIT_DEFAULT_GCN_TAG";

export function deleteDefaultGcnTag(id) {
  return API.DELETE(`/api/default_gcn_tag/${id}`, DELETE_DEFAULT_GCN_TAG);
}

export const fetchDefaultGcnTags = () =>
  API.GET("/api/default_gcn_tag", FETCH_DEFAULT_GCN_TAGS);

export const submitDefaultGcnTag = (default_plan) =>
  API.POST(`/api/default_gcn_tag`, SUBMIT_DEFAULT_GCN_TAG, default_plan);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_DEFAULT_GCN_TAGS) {
    dispatch(fetchDefaultGcnTags());
  }
});

const reducer = (
  state = {
    defaultGcnTagList: [],
  },
  action,
) => {
  switch (action.type) {
    case FETCH_DEFAULT_GCN_TAGS_OK: {
      const default_gcn_tags = action.data;
      return {
        ...state,
        defaultGcnTagList: default_gcn_tags,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("default_gcn_tags", reducer);
