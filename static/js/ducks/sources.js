import messageHandler from "baselayer/MessageHandler";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import * as API from "../API";
import store from "../store";
import * as sourceActions from "./source";

dayjs.extend(relativeTime);
dayjs.extend(utc);

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

const FETCH_SOURCE_AND_MERGE = "skyportal/FETCH_SOURCE_AND_MERGE";
const FETCH_SOURCE_AND_MERGE_OK = "skyportal/FETCH_SOURCE_AND_MERGE_OK";

const FETCH_GCNEVENT_SOURCES = "skyportal/FETCH_GCNEVENT_SOURCES";
const FETCH_GCNEVENT_SOURCES_OK = "skyportal/FETCH_GCNEVENT_SOURCES_OK";

const addFilterParamDefaults = (filterParams) => {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  if (!Object.keys(filterParams).includes("numPerPage")) {
    filterParams.numPerPage = 10;
  }
  filterParams.includePhotometryExists = true;
  filterParams.includePeriodExists = true;
  filterParams.includeSpectrumExists = true;
  filterParams.includeColorMagnitude = true;
  filterParams.includeThumbnails = true;
  filterParams.includeDetectionStats = true;
};

export function fetchSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  return API.GET("/api/sources", FETCH_SOURCES, filterParams);
}

export function fetchSavedGroupSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  return API.GET("/api/sources", FETCH_SAVED_GROUP_SOURCES, filterParams);
}

export function fetchPendingGroupSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  filterParams.pendingOnly = true;
  return API.GET("/api/sources", FETCH_PENDING_GROUP_SOURCES, filterParams);
}

export function fetchFavoriteSources(filterParams = {}) {
  addFilterParamDefaults(filterParams);
  filterParams.listName = "favorites";
  return API.GET("/api/sources", FETCH_FAVORITE_SOURCES, filterParams);
}

export function fetchGcnEventSources(dateobs, filterParams = {}) {
  addFilterParamDefaults(filterParams);
  filterParams.localizationDateobs = dateobs;

  if (!Object.keys(filterParams).includes("startDate")) {
    if (dateobs) {
      filterParams.startDate = dayjs(dateobs).format("YYYY-MM-DD HH:mm:ss");
    }
  }

  if (!Object.keys(filterParams).includes("endDate")) {
    if (dateobs) {
      filterParams.endDate = dayjs(dateobs)
        .add(7, "day")
        .format("YYYY-MM-DD HH:mm:ss");
    }
  }

  if (!Object.keys(filterParams).includes("include_localization_status")) {
    if (dateobs) {
      filterParams.includeLocalizationStatus = true;
    }
  }

  filterParams.includeGeoJSON = true;
  return API.GET("/api/sources", FETCH_GCNEVENT_SOURCES, filterParams);
}

const initialState = {
  sources: null,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { sources } = getState();
  if (actionType === REFRESH_FAVORITE_SOURCES) {
    if (window.location.pathname === "/favorites") {
      dispatch(fetchFavoriteSources());
    }
  }

  const { gcnEvent } = getState();
  if (actionType === FETCH_GCNEVENT_SOURCES) {
    if (gcnEvent && gcnEvent.id === payload.gcnEvent.id) {
      dispatch(fetchGcnEventSources(gcnEvent.dateobs));
    }
  }

  if (actionType === sourceActions.REFRESH_SOURCE) {
    let fetched = false;
    ["latest", "savedGroupSources", "favorites", "pendingGroupSources"].forEach(
      (branchName) => {
        if (sources[branchName]?.sources && !fetched) {
          sources[branchName].sources.forEach((obj) => {
            if (obj.internal_key === payload.obj_key && !fetched) {
              dispatch(
                sourceActions.fetchSource(obj.id, FETCH_SOURCE_AND_MERGE)
              );
              fetched = true;
            }
          });
        }
      }
    );
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
    case FETCH_SOURCE_AND_MERGE_OK: {
      const newState = {};
      [
        "latest",
        "savedGroupSources",
        "favorites",
        "pendingGroupSources",
      ].forEach((branchName) => {
        if (state[branchName]?.sources?.length) {
          newState[branchName] = {
            ...state[branchName],
            sources: state[branchName].sources.map((obj) =>
              obj.id === action.data.id ? action.data : obj
            ),
          };
        }
      });
      return {
        ...state,
        ...newState,
      };
    }
    case FETCH_GCNEVENT_SOURCES_OK: {
      return {
        ...state,
        gcnEventSources: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sources", reducer);
