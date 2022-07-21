import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SOURCES_IN_GCN = "skyportal/FETCH_SOURCES_IN_GCN";
const FETCH_SOURCES_IN_GCN_OK = "skyportal/FETCH_SOURCES_IN_GCN_OK";

const SUBMIT_SOURCE_IN_GCN = "skyportal/SUBMIT_SOURCE_IN_GCN";

const DELETE_SOURCE_IN_GCN = "skyportal/DELETE_SOURCE_IN_GCN";

const PATCH_SOURCE_IN_GCN = "skyportal/PATCH_SOURCE_IN_GCN";

export const fetchSourcesInGcn = (dateobs, data) => API.GET(`/api/sources_in_gcn/${dateobs}`, SUBMIT_SOURCE_IN_GCN, data);

export const submitSourceInGcn = (dateobs, data) => API.POST(`/api/sources_in_gcn/${dateobs}`, SUBMIT_SOURCE_IN_GCN, data);

export const deleteSourceInGcn = (dateobs, source_id, data) => API.DELETE(`/api/sources_in_gcn/${dateobs}/${source_id}`, DELETE_SOURCE_IN_GCN, data);

export const patchSourceInGcn = (dateobs, source_id, data) => API.PUT(`/api/sources_in_gcn/${dateobs}/${source_id}`, PATCH_SOURCE_IN_GCN, data);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const data = payload.data;
  if (actionType === FETCH_SOURCES_IN_GCN) {
    dispatch(fetchSourceIn(data.dateobs, data.localization_name));
  }
});

const reducer = (
  state = { sourcesInGcn: [] },
  action
) => {
  switch (action.type) {
    case FETCH_SOURCES_IN_GCN_OK: {
      const sourcesInGcn = action.data;
      return {
        ...state,
        sourcesInGcn,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sourcesInGcn", reducer);
