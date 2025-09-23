import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_MMADETECTOR = "skyportal/REFRESH_MMADETECTOR";

const FETCH_MMADETECTOR = "skyportal/FETCH_MMADETECTOR";
const FETCH_MMADETECTOR_OK = "skyportal/FETCH_MMADETECTOR_OK";

const SUBMIT_MMADETECTOR = "skyportal/SUBMIT_MMADETECTOR";

const REFRESH_MMADETECTOR_LIST = "skyportal/REFRESH_MMADETECTOR_LIST";

const FETCH_MMADETECTOR_LIST = "skyportal/FETCH_MMADETECTOR_LIST";
const FETCH_MMADETECTOR_LIST_OK = "skyportal/FETCH_MMADETECTOR_LIST_OK";

export const fetchMMADetector = (id) =>
  API.GET(`/api/mmadetector/${id}`, FETCH_MMADETECTOR);

export const submitMMADetector = (run) =>
  API.POST(`/api/mmadetector`, SUBMIT_MMADETECTOR, run);

export const fetchMMADetectors = () =>
  API.GET("/api/mmadetector", FETCH_MMADETECTOR_LIST);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { mmadetector } = getState();
  if (actionType === REFRESH_MMADETECTOR) {
    const { mmadetector_id } = payload;
    if (mmadetector_id === mmadetector?.id) {
      dispatch(fetchMMADetector(mmadetector_id));
    }
  }
  if (actionType === REFRESH_MMADETECTOR_LIST) {
    dispatch(fetchMMADetectors());
  }
});

const reducer_mmadetector = (state = {}, action) => {
  switch (action.type) {
    case FETCH_MMADETECTOR_OK: {
      const mmadetector = action.data;
      return {
        ...state,
        ...mmadetector,
      };
    }
    default:
      return state;
  }
};

const reducer_mmadetectors = (state = { mmadetectorList: [] }, action) => {
  switch (action.type) {
    case FETCH_MMADETECTOR_LIST_OK: {
      const mmadetectorList = action.data;
      return {
        ...state,
        mmadetectorList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("mmadetector", reducer_mmadetector);
store.injectReducer("mmadetectors", reducer_mmadetectors);
