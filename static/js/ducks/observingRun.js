import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_OBSERVING_RUN = "skyportal/REFRESH_OBSERVING_RUN";

const FETCH_OBSERVING_RUN = "skyportal/FETCH_OBSERVING_RUN";
const FETCH_OBSERVING_RUN_OK = "skyportal/FETCH_OBSERVING_RUN_OK";

const SUBMIT_OBSERVING_RUN = "skyportal/SUBMIT_OBSERVING_RUN";

const MODIFY_OBSERVING_RUN = "skyportal/MODIFY_OBSERVING_RUN";

const DELETE_OBSERVING_RUN = "skyportal/DELETE_OBSERVING_RUN";

const PUT_OBSERVING_RUN_NOT_OBSERVED =
  "skyportal/PUT_OBSERVING_RUN_NOT_OBSERVED";

export const putObservingRunNotObserved = (id) =>
  API.PUT(
    `/api/observing_run/${id}/not_observed`,
    PUT_OBSERVING_RUN_NOT_OBSERVED,
    { current_status: "pending", new_status: "not observed" },
  );

export const fetchObservingRun = (id) =>
  API.GET(`/api/observing_run/${id}`, FETCH_OBSERVING_RUN);

export const modifyObservingRun = (id, run) =>
  API.PUT(`/api/observing_run/${id}`, MODIFY_OBSERVING_RUN, run);

export const submitObservingRun = (run) =>
  API.POST(`/api/observing_run`, SUBMIT_OBSERVING_RUN, run);

export function deleteObservingRun(observingRunID) {
  return API.DELETE(
    `/api/observing_run/${observingRunID}`,
    DELETE_OBSERVING_RUN,
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { observingRun } = getState();
  if (actionType === REFRESH_OBSERVING_RUN) {
    const { run_id } = payload;
    if (run_id === observingRun?.id) {
      dispatch(fetchObservingRun(run_id));
    }
  }
});

const reducer = (state = {}, action) => {
  switch (action.type) {
    case FETCH_OBSERVING_RUN_OK: {
      const observingrun = action.data;
      return {
        ...state,
        ...observingrun,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("observingRun", reducer);
