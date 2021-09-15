import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import store from "../store";

const FETCH_SOURCES = "skyportal/FETCH_SOURCES";
const FETCH_SOURCES_OK = "skyportal/FETCH_SOURCES_OK";
const FETCH_SOURCES_FAIL = "skyportal/FETCH_SOURCES_FAIL";

const FETCH_SAVED_GROUP_SOURCES = "skyportal/FETCH_SAVED_GROUP_SOURCES";
const FETCH_SAVED_GROUP_SOURCES_OK = "skyportal/FETCH_SAVED_GROUP_SOURCES_OK";

const FETCH_PENDING_GROUP_SOURCES = "skyportal/FETCH_PENDING_GROUP_SOURCES";
const FETCH_PENDING_GROUP_SOURCES_OK =
  "skyportal/FETCH_PENDING_GROUP_SOURCES_OK";

const FETCH_FAVORITE_SOURCES = "skyportal/FETCH_FAVORITE_SOURCES";
const FETCH_FAVORITE_SOURCES_OK = "skyportal/FETCH_FAVORITE_SOURCES_OK";

const REFRESH_FAVORITE_SOURCES = "skyportal/REFRESH_FAVORITE_SOURCES";

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
  filterParams.includePhotometryExists = true;
  filterParams.includeSpectrumExists = true;
  filterParams.includeColorMagnitude = true;
  filterParams.includeThumbnails = true;
  filterParams.includeDetectionStats = true;
  return API.GET("/api/sources", FETCH_SOURCES, filterParams);
}

export function fetchSavedGroupSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  filterParams.includePhotometryExists = true;
  filterParams.includeSpectrumExists = true;
  filterParams.includeColorMagnitude = true;
  filterParams.includeThumbnails = true;
  filterParams.includeDetectionStats = true;
  return API.GET("/api/sources", FETCH_SAVED_GROUP_SOURCES, filterParams);
}

export function fetchPendingGroupSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  filterParams.pendingOnly = true;
  filterParams.includePhotometryExists = true;
  filterParams.includeSpectrumExists = true;
  filterParams.includeColorMagnitude = true;
  filterParams.includeThumbnails = true;
  filterParams.includeDetectionStats = true;
  return API.GET("/api/sources", FETCH_PENDING_GROUP_SOURCES, filterParams);
}

export function fetchFavoriteSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  filterParams.includePhotometryExists = true;
  filterParams.includeSpectrumExists = true;
  filterParams.listName = "favorites";
  filterParams.includeColorMagnitude = true;
  filterParams.includeThumbnails = true;
  filterParams.includeDetectionStats = true;
  return API.GET("/api/sources", FETCH_FAVORITE_SOURCES, filterParams);
}

const initialState = {
  sources: null,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_FAVORITE_SOURCES) {
    if (window.location.pathname === "/favorites") {
      dispatch(fetchFavoriteSources());
    }
  }
});

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
    case FETCH_SAVED_GROUP_SOURCES_OK: {
      return {
        ...state,
        savedGroupSources: action.data,
      };
    }
    case FETCH_PENDING_GROUP_SOURCES_OK: {
      return {
        ...state,
        pendingGroupSources: action.data,
      };
    }
    case FETCH_FAVORITE_SOURCES_OK: {
      return {
        ...state,
        favorites: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sources", reducer);
