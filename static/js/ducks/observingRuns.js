import * as API from '../API';
import store from '../store';

export const FETCH_OBSERVING_RUNS = 'skyportal/FETCH_OBSERVING_RUNS';
export const FETCH_OBSERVING_RUNS_OK = 'skyportal/FETCH_OBSERVING_RUNS_OK';

export const fetchObservingRuns = () => (
  API.GET('/api/observing_run', FETCH_OBSERVING_RUNS)
);

const reducer = (state={ observingRunList: [] }, action) => {
  switch (action.type) {
    case FETCH_OBSERVING_RUNS_OK: {
      const observingRunList = action.data;
      return {
        ...state,
        observingRunList
      };
    }
    default:
      return state;
  }
};

store.injectReducer('observingRuns', reducer);
