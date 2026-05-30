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

export const putObservingRunNotObserved = (id: number | string) =>
  API.PUT(
    `/api/observing_run/${id}/not_observed`,
    PUT_OBSERVING_RUN_NOT_OBSERVED,
    { current_status: "pending", new_status: "not observed" },
  );

export const fetchObservingRun = (id: number | string) =>
  API.GET(`/api/observing_run/${id}`, FETCH_OBSERVING_RUN);

export const modifyObservingRun = (
  id: number | string,
  run: Record<string, any>,
) => API.PUT(`/api/observing_run/${id}`, MODIFY_OBSERVING_RUN, run);

export const submitObservingRun = (run: Record<string, any>) =>
  API.POST(`/api/observing_run`, SUBMIT_OBSERVING_RUN, run);

export function deleteObservingRun(observingRunID: number | string) {
  return API.DELETE(
    `/api/observing_run/${observingRunID}`,
    DELETE_OBSERVING_RUN,
  );
}

// Websocket message handler
messageHandler.add(
  (actionType: any, payload: any, dispatch: any, getState: any) => {
    const { observingRun } = getState();
    if (actionType === REFRESH_OBSERVING_RUN) {
      const { run_id } = payload;
      if (run_id === observingRun?.id) {
        dispatch(fetchObservingRun(run_id));
      }
    }
  },
);

const reducer = (
  state: Record<string, any> = {},
  action: { type: string; data?: any },
): Record<string, any> => {
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
