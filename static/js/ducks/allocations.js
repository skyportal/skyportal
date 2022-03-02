import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_ALLOCATIONS = "skyportal/FETCH_ALLOCATIONS";
const FETCH_ALLOCATIONS_OK = "skyportal/FETCH_ALLOCATIONS_OK";

const REFRESH_ALLOCATIONS = "skyportal/REFRESH_ALLOCATIONS";

// eslint-disable-next-line import/prefer-default-export
export const fetchAllocations = (params = {}) =>
  API.GET("/api/allocation", FETCH_ALLOCATIONS, params);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_ALLOCATIONS) {
    dispatch(fetchAllocations());
  }
});

const reducer = (state = { allocationList: [] }, action) => {
  switch (action.type) {
    case FETCH_ALLOCATIONS_OK: {
      const allocationList = action.data;
      return {
        ...state,
        allocationList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("allocations", reducer);
