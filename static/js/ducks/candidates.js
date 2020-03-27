import messageHandler from 'baselayer/MessageHandler';

import * as API from '../API';
import store from '../store';


export const FETCH_CANDIDATES = 'skyportal/FETCH_CANDIDATES';
export const FETCH_CANDIDATES_OK = 'skyportal/FETCH_CANDIDATES_OK';
export const FETCH_CANDIDATES_FAIL = 'skyportal/FETCH_CANDIDATES_FAIL';


export const fetchCandidates = (filterParams={}) => {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/candidates?${queryString}`, FETCH_CANDIDATES);
};

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_CANDIDATES) {
    dispatch(fetchCandidates());
  }
});

const initialState = {
  candidates: [],
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  candidateNumberingStart: 0,
  candidateNumberingEnd: 0
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_CANDIDATES_OK: {
      const { candidates, pageNumber, lastPage, totalMatches, candidateNumberingStart,
        candidateNumberingEnd } = action.data;
      return {
        ...state,
        candidates,
        pageNumber,
        lastPage,
        totalMatches,
        candidateNumberingStart,
        candidateNumberingEnd
      };
    }
    default:
      return state;
  }
};

store.injectReducer('candidates', reducer);
