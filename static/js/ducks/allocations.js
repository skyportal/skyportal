import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_ALLOCATIONS = "skyportal/FETCH_ALLOCATIONS";
const FETCH_ALLOCATIONS_OK = "skyportal/FETCH_ALLOCATIONS_OK";

const FETCH_ALLOCATIONS_API_OBSPLAN = "skyportal/FETCH_ALLOCATIONS_API_OBSPLAN";
const FETCH_ALLOCATIONS_API_OBSPLAN_OK =
  "skyportal/FETCH_ALLOCATIONS_API_OBSPLAN_OK";

const FETCH_ALLOCATIONS_API_CLASSNAME =
  "skyportal/FETCH_ALLOCATIONS_API_CLASSNAME";
const FETCH_ALLOCATIONS_API_CLASSNAME_OK =
  "skyportal/FETCH_ALLOCATIONS_API_CLASSNAME_OK";

const REFRESH_ALLOCATIONS = "skyportal/REFRESH_ALLOCATIONS";

// eslint-disable-next-line import/prefer-default-export
export const fetchAllocations = () =>
  API.GET("/api/allocation", FETCH_ALLOCATIONS);

export function fetchAllocationsApiObsplan(params = {}) {
  const apiQueryDefaults = { apiType: "api_classname_obsplan" };
  return API.GET("/api/allocation", FETCH_ALLOCATIONS_API_OBSPLAN, {
    ...apiQueryDefaults,
    ...params,
  });
}

export function fetchAllocationsApiClassname(params = {}) {
  const apiQueryDefaults = { apiType: "api_classname" };
  return API.GET("/api/allocation", FETCH_ALLOCATIONS_API_CLASSNAME, {
    ...apiQueryDefaults,
    ...params,
  });
}

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_ALLOCATIONS) {
    dispatch(fetchAllocations());
  }
});

const reducer = (
  state = {
    allocationList: [],
    allocationListApiObsplan: [],
    allocationListApiClassname: [],
  },
  action,
) => {
  switch (action.type) {
    case FETCH_ALLOCATIONS_OK: {
      const allocationList = action.data;
      return {
        ...state,
        allocationList,
      };
    }
    case FETCH_ALLOCATIONS_API_OBSPLAN_OK: {
      const allocationListApiObsplan = action.data;
      return {
        ...state,
        allocationListApiObsplan,
      };
    }
    case FETCH_ALLOCATIONS_API_CLASSNAME_OK: {
      const allocationListApiClassname = action.data;
      return {
        ...state,
        allocationListApiClassname,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("allocations", reducer);
