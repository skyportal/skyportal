import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_OBSERVING_RUNS = "skyportal/FETCH_OBSERVING_RUNS";
const FETCH_OBSERVING_RUNS_OK = "skyportal/FETCH_OBSERVING_RUNS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchObservingRuns = () =>
  API.GET("/api/observing_run", FETCH_OBSERVING_RUNS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_OBSERVING_RUNS) {
    dispatch(fetchObservingRuns());
  }
});

const reducer = (state = { observingRunList: [] }, action) => {
  switch (action.type) {
    case FETCH_OBSERVING_RUNS_OK: {
      const observingRunList = action.data;
      return {
        ...state,
        observingRunList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("observingRuns", reducer);
