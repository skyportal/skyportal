import * as API from '../API';
import store from '../store';

const FETCH_OBSERVING_RUNS = 'skyportal/FETCH_OBSERVING_RUNS';
const FETCH_OBSERVING_RUNS_OK = 'skyportal/FETCH_OBSERVING_RUNS_OK';

export const fetchObservingRuns = () => (
  API.GET('/api/observing_run', FETCH_OBSERVING_RUNS)
);

const reducer = (state={ observingRunList: [] }, action) => {
  switch (action.type) {
    case FETCH_OBSERVING_RUNS_OK: {
      const observingruns = action.data;
      return {
        ...state,
        observingRunList: observingruns
      };
    }
    default:
      return state;
  }
};

store.injectReducer('observingRuns', reducer);
