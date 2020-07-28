import * as API from '../API';
import store from '../store';
import { REFRESH_SOURCE } from "./source";

export const FETCH_OBSERVING_RUN = 'skyportal/FETCH_OBSERVING_RUN';
export const FETCH_OBSERVING_RUN_OK = 'skyportal/FETCH_OBSERVING_RUN_OK';

export const fetchObservingRun = (id) => (
  API.GET(`/api/observing_run/${id}`, FETCH_OBSERVING_RUN)
);


const reducer = (state={ assignments: [] }, action) => {
  switch (action.type) {
    case FETCH_OBSERVING_RUN_OK: {
      const observingrun = action.data;
      return {
        ...state,
        ...observingrun
      };
    }
    /*TODO: Normalize state shape to eliminate the action processor below.
    The implementation below re-fetches the entire run when one of the run's
    sources is updated. With a normalized state tree, this (potentially large) GET
    could be avoided in favor of a single update to the Source entity on the frontend.
     */

    case REFRESH_SOURCE:
      const { obj_id } = action.data;
      const current_ids = state.assignments.map((a) => (a.obj_id));
      if (state.id && obj_id in current_ids){
        fetchObservingRun(state.id);
      }
      return state;

    default:
      return state;
  }
};

store.injectReducer('observingRun', reducer);
