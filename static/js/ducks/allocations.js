import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_ALLOCATIONS = "skyportal/FETCH_ALLOCATIONS";
const FETCH_ALLOCATIONS_OK = "skyportal/FETCH_ALLOCATIONS_OK";

const FETCH_ALLOCATIONS_API_OBSPLAN = "skyportal/FETCH_ALLOCATIONS_API_OBSPLAN";
const FETCH_ALLOCATIONS_API_OBSPLAN_OK =
  "skyportal/FETCH_ALLOCATIONS_API_OBSPLAN_OK";

const REFRESH_ALLOCATIONS = "skyportal/REFRESH_ALLOCATIONS";

// eslint-disable-next-line import/prefer-default-export
export const fetchAllocations = (params = {}) =>
  API.GET("/api/allocation", FETCH_ALLOCATIONS, params);

export const fetchAllocationsApiObsplan = (params = {}) =>
  API.GET("/api/allocation", FETCH_ALLOCATIONS_API_OBSPLAN, params);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_ALLOCATIONS) {
    dispatch(fetchAllocations());
  }
});

const reducer = (
  state = { allocationList: [], allocationListApiObsplan: [] },
  action
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
    default:
      return state;
  }
};

store.injectReducer("allocations", reducer);
