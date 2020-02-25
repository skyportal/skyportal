import * as API from '../API';
import store from '../store';


export const FETCH_CANDIDATES = 'skyportal/FETCH_CANDIDATES';
export const FETCH_CANDIDATES_OK = 'skyportal/FETCH_CANDIDATES_OK';
export const FETCH_CANDIDATES_FAIL = 'skyportal/FETCH_CANDIDATES_FAIL';


export const fetchCandidates = (pageNumber = 1) => (
  API.GET(`/api/sources?pageNumber=${pageNumber}&candidateScanningPage=true`,
          FETCH_CANDIDATES)
);

const initialState = {
  candidateList: [],
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  sourceNumberingStart: 0,
  sourceNumberingEnd: 0
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_CANDIDATES_OK: {
      const { sources, pageNumber, lastPage, totalMatches, sourceNumberingStart,
              sourceNumberingEnd } = action.data;
      const candidateList = sources;
      return {
        ...state,
        candidateList,
        pageNumber,
        lastPage,
        totalMatches,
        sourceNumberingStart,
        sourceNumberingEnd
      };
    }
    default:
      return state;
  }
};

store.injectReducer('candidates', reducer);
