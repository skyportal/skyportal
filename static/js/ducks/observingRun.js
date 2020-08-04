import * as API from '../API';
import store from '../store';

export const FETCH_OBSERVING_RUN = 'skyportal/FETCH_OBSERVING_RUN';
export const FETCH_OBSERVING_RUN_OK = 'skyportal/FETCH_OBSERVING_RUN_OK';

export const FETCH_ASSIGNMENT = 'skyportal/FETCH_ASSIGNMENT';
export const FETCH_ASSIGNMENT_OK = 'skyportal/FETCH_ASSIGNMENT_OK';

export const fetchObservingRun = (id) => (
  API.GET(`/api/observing_run/${id}`, FETCH_OBSERVING_RUN)
);

export const fetchAssignment = (id) => (
  API.GET(`/api/assignment/${id}`, FETCH_ASSIGNMENT)
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

    case FETCH_ASSIGNMENT_OK: {
      const assignment = action.data;
      const assignment_ids = state.assignments.map((a) => a.id);
      if (assignment_ids.includes(assignment.id)) {
        const index = assignment_ids.indexOf(assignment.id);
        state.assignments[index] = assignment;
      } else {
        state.assignments.push(assignment);
      }
      return { ...state };
    }

    default:
      return state;
  }
};

store.injectReducer('observingRun', reducer);
