import * as API from "../API";
import store from "../store";
import { brokerFilterBase } from "./brokerFilterTarget";

export const FETCH_FILTER_VERSION = "skyportal/FETCH_FILTER_VERSION";
export const FETCH_FILTER_VERSION_OK = "skyportal/FETCH_FILTER_VERSION_OK";
export const FETCH_FILTER_VERSION_ERROR =
  "skyportal/FETCH_FILTER_VERSION_ERROR";
export const FETCH_FILTER_VERSION_FAIL = "skyportal/FETCH_FILTER_VERSION_FAIL";

export const ADD_FILTER_VERSION = "skyportal/ADD_FILTER_VERSION";
export const ADD_FILTER_VERSION_OK = "skyportal/ADD_FILTER_VERSION_OK";

export const EDIT_FILTER_VERSION = "skyportal/EDIT_FILTER_VERSION";
export const EDIT_FILTER_VERSION_OK = "skyportal/EDIT_FILTER_VERSION_OK";

export const ADD_GROUP_FILTER = "skyportal/ADD_GROUP_FILTER";
export const ADD_GROUP_FILTER_OK = "skyportal/ADD_GROUP_FILTER_OK";

export const EDIT_UPDATE_ANNOTATIONS = "skyportal/EDIT_UPDATE_ANNOTATIONS";
export const EDIT_UPDATE_ANNOTATIONS_OK =
  "skyportal/EDIT_UPDATE_ANNOTATIONS_OK";

export const EDIT_AUTOSAVE = "skyportal/EDIT_AUTOSAVE";
export const EDIT_AUTOSAVE_OK = "skyportal/EDIT_AUTOSAVE_OK";

export const EDIT_AUTO_FOLLOWUP = "skyportal/EDIT_AUTO_FOLLOWUP";
export const EDIT_AUTO_FOLLOWUP_OK = "skyportal/EDIT_AUTO_FOLLOWUP_OK";

const UPDATE_GROUP_FILTER = "skyportal/UPDATE_GROUP_FILTER";
const UPDATE_GROUP_FILTER_OK = "skyportal/UPDATE_GROUP_FILTER_OK";

const DELETE_GROUP_FILTER = "skyportal/DELETE_GROUP_FILTER";
const DELETE_GROUP_FILTER_OK = "skyportal/DELETE_GROUP_FILTER_OK";

export function fetchFilterVersion(id) {
  return API.GET(`${brokerFilterBase()}/filters/${id}`, FETCH_FILTER_VERSION);
}

export function editFilterVersion({ filter_id, active, active_fid }) {
  return API.PATCH(
    `${brokerFilterBase()}/filters/${filter_id}`,
    EDIT_FILTER_VERSION,
    {
      active,
      active_fid,
    },
  );
}

export function addGroupFilter({ name, group_id, stream_id, altdata }) {
  return API.POST("/api/filters", ADD_GROUP_FILTER, {
    name,
    group_id,
    stream_id,
    altdata,
  });
}

export function editAutosave({ filter_id, autoSave }) {
  return API.PATCH(
    `${brokerFilterBase()}/filters/${filter_id}`,
    EDIT_AUTOSAVE,
    {
      autoSave,
    },
  );
}

export function deleteGroupFilter({ filter_id }) {
  return API.DELETE(
    `${brokerFilterBase()}/filters/${filter_id}`,
    DELETE_GROUP_FILTER,
  );
}

export function editUpdateAnnotations({ filter_id, autoAnnotate }) {
  return API.PATCH(
    `${brokerFilterBase()}/filters/${filter_id}`,
    EDIT_UPDATE_ANNOTATIONS,
    {
      autoAnnotate,
    },
  );
}

export function editAutoFollowup({ filter_id, autoFollowup }) {
  return API.PATCH(
    `${brokerFilterBase()}/filters/${filter_id}`,
    EDIT_AUTO_FOLLOWUP,
    {
      autoFollowup,
    },
  );
}

export function updateGroupFilter(filter_id, altdata, filters, name) {
  return API.POST(
    `${brokerFilterBase()}/filters/${filter_id}`,
    UPDATE_GROUP_FILTER,
    {
      altdata,
      filters,
      name,
    },
  );
}

const reducer = (state = {}, action) => {
  switch (action.type) {
    case UPDATE_GROUP_FILTER_OK:
    case FETCH_FILTER_VERSION_OK: {
      return action.data;
    }
    case FETCH_FILTER_VERSION_FAIL:
    case FETCH_FILTER_VERSION_ERROR: {
      return {};
    }
    default:
      return state;
  }
};

store.injectReducer("boom_filter_v", reducer);
