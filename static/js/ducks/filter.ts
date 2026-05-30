import * as API from "../API";
import store from "../store";

const FETCH_FILTER = "skyportal/FETCH_FILTER";
const FETCH_FILTER_OK = "skyportal/FETCH_FILTER_OK";
const FETCH_FILTER_ERROR = "skyportal/FETCH_FILTER_ERROR";
const FETCH_FILTER_FAIL = "skyportal/FETCH_FILTER_FAIL";

const ADD_GROUP_FILTER = "skyportal/ADD_GROUP_FILTER";

const DELETE_GROUP_FILTER = "skyportal/DELETE_GROUP_FILTER";

export function fetchFilter(id: number | string) {
  return API.GET(`/api/filters/${id}`, FETCH_FILTER);
}

export function addGroupFilter({
  name,
  group_id,
  stream_id,
}: {
  name: string;
  group_id: number | string;
  stream_id: number | string;
}) {
  return API.POST("/api/filters", ADD_GROUP_FILTER, {
    name,
    group_id,
    stream_id,
  });
}

export function deleteGroupFilter({
  filter_id,
}: {
  filter_id: number | string;
}) {
  return API.DELETE(`/api/filters/${filter_id}`, DELETE_GROUP_FILTER);
}

type FilterState = Record<string, any>;

interface FilterAction {
  type: string;
  data?: any;
}

const reducer = (
  state: FilterState = {},
  action: FilterAction,
): FilterState => {
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

store.injectReducer("filter", reducer);
