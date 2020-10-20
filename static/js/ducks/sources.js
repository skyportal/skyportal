import * as API from "../API";
import store from "../store";

export const FETCH_SOURCES = "skyportal/FETCH_SOURCES";
export const FETCH_SOURCES_OK = "skyportal/FETCH_SOURCES_OK";
export const FETCH_SOURCES_FAIL = "skyportal/FETCH_SOURCES_FAIL";

export const FETCH_GROUP_SOURCES = "skyportal/FETCH_GROUP_SOURCES";
export const FETCH_GROUP_SOURCES_OK = "skyportal/FETCH_GROUP_SOURCES_OK";
export const FETCH_GROUP_SOURCES_FAIL = "skyportal/FETCH_GROUP_SOURCES_FAIL";

export function fetchSources(filterParams = {}) {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/sources?${queryString}`, FETCH_SOURCES);
}

export function fetchGroupSources(filterParams = {}) {
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/sources?${queryString}`, FETCH_GROUP_SOURCES);
}

const initialState = {
  latest: null,
  groupSources: null,
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  numberingStart: 0,
  numberingEnd: 0,
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_SOURCES: {
      return {
        ...state,
        queryInProgress: action.parameters.body.pageNumber === undefined,
      };
    }
    case FETCH_SOURCES_OK: {
      const {
        sources,
        pageNumber,
        lastPage,
        totalMatches,
        numberingStart,
        numberingEnd,
      } = action.data;
      return {
        ...state,
        latest: sources,
        queryInProgress: false,
        pageNumber,
        lastPage,
        totalMatches,
        numberingStart,
        numberingEnd,
      };
    }
    case FETCH_SOURCES_FAIL: {
      return {
        ...state,
        queryInProgress: false,
      };
    }
    case FETCH_GROUP_SOURCES: {
      return {
        ...state,
        queryInProgress: action.parameters.body.pageNumber === undefined,
      };
    }
    case FETCH_GROUP_SOURCES_OK: {
      const { sources } = action.data;
      return {
        ...state,
        groupSources: sources,
        queryInProgress: false,
      };
    }
    case FETCH_GROUP_SOURCES_FAIL: {
      return {
        ...state,
        queryInProgress: false,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sources", reducer);
