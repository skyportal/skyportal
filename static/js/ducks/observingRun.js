import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import { REFRESH_SOURCE } from "./source";

export const FETCH_OBSERVING_RUN = "skyportal/FETCH_OBSERVING_RUN";
export const FETCH_OBSERVING_RUN_OK = "skyportal/FETCH_OBSERVING_RUN_OK";

export const FETCH_ASSIGNMENT = "skyportal/FETCH_ASSIGNMENT";
export const FETCH_ASSIGNMENT_OK = "skyportal/FETCH_ASSIGNMENT_OK";

export const fetchObservingRun = (id) =>
  API.GET(`/api/observing_run/${id}`, FETCH_OBSERVING_RUN);

export const fetchAssignment = (id) =>
  API.GET(`/api/assignment/${id}`, FETCH_ASSIGNMENT);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { observingRun } = getState();

  /* TODO: Normalize state shape to eliminate the action processor below.
  The implementation below re-fetches the entire run when one of the run's
  sources is updated. With a normalized state tree, this (potentially large) GET
  could be avoided in favor of a single update to the Source entity on the frontend.
   */

  if (actionType === REFRESH_SOURCE) {
    const { obj_id } = payload;
    const assignment = observingRun.assignments.filter(
      (a) => a.obj_id === obj_id
    )[0];
    if (assignment) {
      dispatch(fetchAssignment(assignment.id));
    }
  }
});

const reducer = (state = { assignments: [] }, action) => {
  switch (action.type) {
    case FETCH_OBSERVING_RUN_OK: {
      const observingrun = action.data;
      return {
        ...state,
        ...observingrun,
      };
    }

    case FETCH_ASSIGNMENT_OK: {
      const assignments = [...state.assignments];
      const assignment = action.data;
      const assignment_ids = assignments.map((a) => a.id);
      if (assignment_ids.includes(assignment.id)) {
        const index = assignment_ids.indexOf(assignment.id);
        assignments[index] = assignment;
      } else {
        assignments.push(assignment);
      }
      return { ...state, assignments };
    }

    default:
      return state;
  }
};

store.injectReducer("observingRun", reducer);
