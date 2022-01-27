import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_ALLOCATION = "skyportal/REFRESH_ALLOCATION";

const FETCH_ALLOCATION = "skyportal/FETCH_ALLOCATION";
const FETCH_ALLOCATION_OK = "skyportal/FETCH_ALLOCATION_OK";

const SUBMIT_ALLOCATION = "skyportal/SUBMIT_ALLOCATION";

export const fetchAllocation = (id) =>
  API.GET(`/api/allocation/${id}`, FETCH_ALLOCATION);

export const submitAllocation = (run) =>
  API.POST(`/api/allocation`, SUBMIT_ALLOCATION, run);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { allocation } = getState();
  if (actionType === REFRESH_ALLOCATION) {
    const { allocation_id } = payload;
    if (allocation_id === allocation?.id) {
      dispatch(fetchAllocation(allocation_id));
    }
  }
});

const reducer = (state = { assignments: [] }, action) => {
  switch (action.type) {
    case FETCH_ALLOCATION_OK: {
      const allocation = action.data;
      return {
        ...state,
        ...allocation,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("allocation", reducer);
