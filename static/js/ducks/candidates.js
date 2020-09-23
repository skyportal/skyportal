import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import fetchCandidate from "./candidate";
import store from "../store";

export const FETCH_CANDIDATES = "skyportal/FETCH_CANDIDATES";
export const FETCH_CANDIDATES_OK = "skyportal/FETCH_CANDIDATES_OK";
export const FETCH_CANDIDATES_FAIL = "skyportal/FETCH_CANDIDATES_FAIL";

export const FETCH_CANDIDATE_AND_MERGE = "skyportal/FETCH_CANDIDATE_AND_MERGE";
export const FETCH_CANDIDATE_AND_MERGE_OK =
  "skyportal/FETCH_CANDIDATE_AND_MERGE_OK";

export const REFRESH_CANDIDATE = "skyportal/REFRESH_CANDIDATE";

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
  } else if (actionType === REFRESH_CANDIDATE) {
    const { candidates } = getState();
    let done = false;
    candidates.candidates.forEach((candidate) => {
      if (candidate.internal_key === payload.id && !done) {
        dispatch(fetchCandidate(candidate.id, FETCH_CANDIDATE_AND_MERGE));
        done = true;
      }
    });
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
    case FETCH_CANDIDATE_AND_MERGE_OK: {
      const candidates = state.candidates.map((candidate) =>
        candidate.id !== action.data.id ? candidate : action.data
      );
      return { ...state, candidates };
    }
    default:
      return state;
  }
};

store.injectReducer("candidates", reducer);
