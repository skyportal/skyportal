import * as API from "../API";
import store from "../store";

export const FETCH_SOURCES = "skyportal/FETCH_SOURCES";
export const FETCH_SOURCES_OK = "skyportal/FETCH_SOURCES_OK";
export const FETCH_SOURCES_FAIL = "skyportal/FETCH_SOURCES_FAIL";

export const FETCH_SAVED_GROUP_SOURCES = "skyportal/FETCH_SAVED_GROUP_SOURCES";
export const FETCH_SAVED_GROUP_SOURCES_OK =
  "skyportal/FETCH_SAVED_GROUP_SOURCES_OK";
export const FETCH_SAVED_GROUP_SOURCES_FAIL =
  "skyportal/FETCH_SAVED_GROUP_SOURCES_FAIL";

export const FETCH_PENDING_GROUP_SOURCES =
  "skyportal/FETCH_PENDING_GROUP_SOURCES";
export const FETCH_PENDING_GROUP_SOURCES_OK =
  "skyportal/FETCH_PENDING_GROUP_SOURCES_OK";
export const FETCH_PENDING_GROUP_SOURCES_FAIL =
  "skyportal/FETCH_PENDING_GROUP_SOURCES_FAIL";

const addFilterParamDefaults = (filterParams) => {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  if (!Object.keys(filterParams).includes("numPerPage")) {
    filterParams.numPerPage = 10;
  }
};

export function fetchSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/sources?${queryString}`, FETCH_SOURCES);
}

export function fetchSavedGroupSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/sources?${queryString}`, FETCH_SAVED_GROUP_SOURCES);
}

export function fetchPendingGroupSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  filterParams.pendingOnly = true;
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/sources?${queryString}`, FETCH_PENDING_GROUP_SOURCES);
}

const initialState = {
  sources: null,
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  numberingStart: 0,
  numberingEnd: 0,
  numPerPage: 10,
};

const reducer = (
  state = {
    latest: initialState,
    savedGroupSources: initialState,
    pendingGroupSources: initialState,
  },
  action
) => {
  switch (action.type) {
    case FETCH_SOURCES: {
      return {
        ...state,
        latest: {
          ...state.latest,
          queryInProgress: action.parameters.body.pageNumber === undefined,
        },
      };
    }
    case FETCH_SOURCES_OK: {
      return {
        ...state,
        latest: { ...action.data, queryInProgress: false },
      };
    }
    case FETCH_SOURCES_FAIL: {
      return {
        ...state,
        latest: { ...state.latest, queryInProgress: false },
      };
    }
    case FETCH_SAVED_GROUP_SOURCES: {
      return {
        ...state,
        savedGroupSources: {
          ...state.savedGroupSources,
          queryInProgress: action.parameters.body.pageNumber === undefined,
        },
      };
    }
    case FETCH_SAVED_GROUP_SOURCES_OK: {
      return {
        ...state,
        savedGroupSources: { ...action.data, queryInProgress: false },
      };
    }
    case FETCH_SAVED_GROUP_SOURCES_FAIL: {
      return {
        ...state,
        savedGroupSources: {
          ...state.savedGroupSources,
          queryInProgress: false,
        },
      };
    }
    case FETCH_PENDING_GROUP_SOURCES: {
      return {
        ...state,
        pendingGroupSources: {
          ...state.pendingGroupSources,
          queryInProgress: action.parameters.body.pageNumber === undefined,
        },
      };
    }
    case FETCH_PENDING_GROUP_SOURCES_OK: {
      return {
        ...state,
        pendingGroupSources: { ...action.data, queryInProgress: false },
      };
    }
    case FETCH_PENDING_GROUP_SOURCES_FAIL: {
      return {
        ...state,
        pendingGroupSources: {
          ...state.pendingGroupSources,
          queryInProgress: false,
        },
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sources", reducer);
