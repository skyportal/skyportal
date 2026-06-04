import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_OBSERVING_RUNS = "skyportal/FETCH_OBSERVING_RUNS";
const FETCH_OBSERVING_RUNS_OK = "skyportal/FETCH_OBSERVING_RUNS_OK";

export const fetchObservingRuns = () =>
  API.GET("/api/observing_run", FETCH_OBSERVING_RUNS);

// Websocket message handler
messageHandler.add(
  (actionType: string, _payload: any, dispatch: AppDispatch) => {
    if (actionType === FETCH_OBSERVING_RUNS) {
      dispatch(fetchObservingRuns());
    }
  },
);

type ObservingRunsState = Record<string, any>;

interface ObservingRunsAction {
  type: string;
  data?: any;
}

const reducer = (
  state: ObservingRunsState = { observingRunList: [] },
  action: ObservingRunsAction,
): ObservingRunsState => {
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
