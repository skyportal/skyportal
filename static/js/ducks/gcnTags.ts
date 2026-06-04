import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GCN_TAGS = "skyportal/FETCH_GCN_TAGS";
const FETCH_GCN_TAGS_OK = "skyportal/FETCH_GCN_TAGS_OK";

const POST_GCN_TAG = "skyportal/POST_GCNTAG";
const DELETE_GCN_TAG = "skyportal/DELETE_GCNTAG";

export const fetchGcnTags = (filterParams: Record<string, any> = {}) =>
  API.GET("/api/gcn_event/tags", FETCH_GCN_TAGS, filterParams);

export function postGcnTag(data: any) {
  return API.POST(`/api/gcn_event/tags`, POST_GCN_TAG, data);
}

export function deleteGcnTag(gcnEventID: number | string, tag: string) {
  return API.DELETE(`/api/gcn_event/tags/${gcnEventID}`, DELETE_GCN_TAG, {
    tag,
  });
}

// Websocket message handler
messageHandler.add((actionType: any, _payload: any, dispatch: any) => {
  if (actionType === FETCH_GCN_TAGS) {
    dispatch(fetchGcnTags());
  }
});

interface GcnTagsAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (state: any = null, action: GcnTagsAction): any => {
  switch (action.type) {
    case FETCH_GCN_TAGS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("gcnTags", reducer);
