import * as API from "../API";
import store from "../store";

export const FETCH_FILTER = "skyportal/FETCH_FILTER";
export const FETCH_FILTER_OK = "skyportal/FETCH_FILTER_OK";
export const FETCH_FILTER_ERROR = "skyportal/FETCH_FILTER_ERROR";
export const FETCH_FILTER_FAIL = "skyportal/FETCH_FILTER_FAIL";

export const ADD_GROUP_FILTER = "skyportal/ADD_GROUP_FILTER";
export const ADD_GROUP_FILTER_OK = "skyportal/ADD_GROUP_FILTER_OK";

export const DELETE_GROUP_FILTER = "skyportal/DELETE_GROUP_FILTER";
export const DELETE_GROUP_FILTER_OK = "skyportal/DELETE_GROUP_FILTER_OK";

export const FETCH_FILTER_V = "skyportal/FETCH_FILTER_V";
export const FETCH_FILTER_V_OK = "skyportal/FETCH_FILTER_V_OK";
export const FETCH_FILTER_V_ERROR = "skyportal/FETCH_FILTER_V_ERROR";
export const FETCH_FILTER_V_FAIL = "skyportal/FETCH_FILTER_V_FAIL";

export const ADD_FILTER_V = "skyportal/ADD_FILTER_V";
export const ADD_FILTER_V_OK = "skyportal/ADD_FILTER_V_OK";

export const EDIT_ACTIVE_FILTER_V = "skyportal/EDIT_ACTIVE_FILTER_V";
export const EDIT_ACTIVE_FILTER_V_OK = "skyportal/EDIT_ACTIVE_FILTER_V_OK";

export const EDIT_ACTIVE_FID_FILTER_V = "skyportal/EDIT_ACTIVE_FID_FILTER_V";
export const EDIT_ACTIVE_FID_FILTER_V_OK =
  "skyportal/EDIT_ACTIVE_FID_FILTER_V_OK";

export const DELETE_FILTER_V = "skyportal/DELETE_FILTER_V";
export const DELETE_FILTER_V_OK = "skyportal/DELETE_FILTER_V_OK";

export function fetchFilter(id) {
  return API.GET(`/api/filters/${id}`, FETCH_FILTER);
}

export function addGroupFilter({ name, group_id, stream_id }) {
  return API.POST("/api/filters", ADD_GROUP_FILTER, {
    name,
    group_id,
    stream_id,
  });
}

export function deleteGroupFilter({ filter_id }) {
  return API.DELETE(`/api/filters/${filter_id}`, DELETE_GROUP_FILTER);
}

export function fetchFilterV(id) {
  return API.GET(`/api/filters/${id}/v`, FETCH_FILTER_V);
}

export function addFilterV({ filter_id, pipeline }) {
  return API.POST(`/api/filters/${filter_id}/v`, ADD_FILTER_V, {
    pipeline,
  });
}

export function editActiveFilterV({ filter_id, active }) {
  return API.PATCH(`/api/filters/${filter_id}/v`, EDIT_ACTIVE_FILTER_V, {
    active,
  });
}

export function editActiveFidFilterV({ filter_id, active_fid }) {
  return API.PATCH(`/api/filters/${filter_id}/v`, EDIT_ACTIVE_FID_FILTER_V, {
    active_fid,
  });
}

export function deleteFilterV(filter_id) {
  return API.DELETE(`/api/filters/${filter_id}/v`, DELETE_FILTER_V);
}

const reducer = (state = {}, action) => {
  switch (action.type) {
    case FETCH_FILTER_OK: {
      return action.data;
    }
    case FETCH_FILTER_FAIL:
    case FETCH_FILTER_ERROR: {
      return {};
    }
    default:
      return state;
  }
};

const reducerV = (state = {}, action) => {
  switch (action.type) {
    case FETCH_FILTER_V_OK: {
      return action.data;
    }
    case FETCH_FILTER_V_FAIL:
    case FETCH_FILTER_V_ERROR: {
      return {};
    }
    default:
      return state;
  }
};

store.injectReducer("filter", reducer);
store.injectReducer("filter_v", reducerV);
