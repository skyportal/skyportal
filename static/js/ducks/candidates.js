import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_CANDIDATES = "skyportal/FETCH_CANDIDATES";
export const FETCH_CANDIDATES_OK = "skyportal/FETCH_CANDIDATES_OK";
export const FETCH_CANDIDATES_FAIL = "skyportal/FETCH_CANDIDATES_FAIL";

export const fetchCandidates = (filterParams = {}) => {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/candidates?${queryString}`, FETCH_CANDIDATES);
};

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === FETCH_CANDIDATES) {
    const { candidates } = getState();
    const pageNumber = candidates.pageNumber ? candidates.pageNumber : 1;
    dispatch(fetchCandidates({ pageNumber }));
  }
});

const initialState = {
  candidates: null,
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  numberingStart: 0,
  numberingEnd: 0,
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_CANDIDATES_OK: {
      const {
        candidates,
        pageNumber,
        lastPage,
        totalMatches,
        numberingStart,
        numberingEnd,
      } = action.data;
      return {
        ...state,
        candidates,
        pageNumber,
        lastPage,
        totalMatches,
        numberingStart,
        numberingEnd,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("candidates", reducer);
