import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GCN_TAGS = "skyportal/FETCH_GCN_TAGS";
const FETCH_GCN_TAGS_OK = "skyportal/FETCH_GCN_TAGS_OK";

const POST_GCN_TAG = "skyportal/POST_GCNTAG";
const DELETE_GCN_TAG = "skyportal/DELETE_GCNTAG";

// eslint-disable-next-line import/prefer-default-export
export const fetchGcnTags = (filterParams = {}) =>
  API.GET("/api/gcn_event/tags", FETCH_GCN_TAGS, filterParams);

export function postGcnTag(data) {
  return API.POST(`/api/gcn_event/tags`, POST_GCN_TAG, data);
}

export function deleteGcnTag(gcnEventID, tag) {
  return API.DELETE(`/api/gcn_event/tags/${gcnEventID}`, DELETE_GCN_TAG, {
    tag,
  });
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_GCN_TAGS) {
    dispatch(fetchGcnTags());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GCN_TAGS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("gcnTags", reducer);
