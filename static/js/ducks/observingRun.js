import * as API from '../API';
import store from '../store';

export const FETCH_OBSERVING_RUN = 'skyportal/FETCH_OBSERVING_RUN';
export const FETCH_OBSERVING_RUN_OK = 'skyportal/FETCH_OBSERVING_RUN_OK';

export const FETCH_OBSERVING_RUN_ASSIGNMENTS = 'skyportal/FETCH_OBSERVING_RUN_ASSIGNMENTS';
export const FETCH_OBSERVING_RUN_ASSIGNMENTS_OK = 'skyportal/FETCH_OBSERVING_RUN_ASSIGNMENTS_OK';


export const fetchObservingRun = (id) => (
  API.GET(`/api/observing_run/${id}`, FETCH_OBSERVING_RUN)
);

export const fetchObservingRunAssignments = (id) => (
  API.GET(`/api/observing_run_assignments/${id}`, FETCH_OBSERVING_RUN_ASSIGNMENTS)
);


const reducer = (state={ observingRun: {}, assignments: {} }, action) => {
  switch (action.type) {
    case FETCH_OBSERVING_RUN_OK: {
      const observingrun = action.data;
      return {
        ...state,
        observingRun: observingrun
      };
    }
    case FETCH_OBSERVING_RUN_ASSIGNMENTS_OK: {
      const assignments = action.data;
      return {
        ...state,
        assignments: assignments
      }
    }
    default:
      return state;
  }
};

store.injectReducer('observingRun', reducer);
