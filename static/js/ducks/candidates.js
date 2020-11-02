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

export const SET_CANDIDATES_ANNOTATION_SORT_OPTIONS =
  "skyportal/SET_CANDIDATES_ANNOTATION_SORT_OPTIONS";

export const FETCH_ANNOTATIONS_INFO = "skyportal/FETCH_ANNOTATIONS_INFO";
export const FETCH_ANNOTATIONS_INFO_OK = "skyportal/FETCH_ANNOTATIONS_INFO_OK";

export const SET_CANDIDATES_FILTER_FORM_DATA =
  "skyportal/SET_CANDIDATES_FILTER_FORM_DATA";

export const fetchCandidates = (filterParams = {}) => {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  const params = new URLSearchParams(filterParams);
  const queryString = params.toString();
  return API.GET(`/api/candidates?${queryString}`, FETCH_CANDIDATES);
};

export const setCandidatesAnnotationSortOptions = (item) => {
  return {
    type: SET_CANDIDATES_ANNOTATION_SORT_OPTIONS,
    item,
  };
};

export const fetchAnnotationsInfo = () => {
  return API.GET(`/api/internal/annotations_info`, FETCH_ANNOTATIONS_INFO);
};

export const setFilterFormData = (formData) => {
  return {
    type: SET_CANDIDATES_FILTER_FORM_DATA,
    formData,
  };
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
    if (candidates.candidates !== null) {
      candidates.candidates.forEach((candidate) => {
        if (candidate.internal_key === payload.id && !done) {
          dispatch(fetchCandidate(candidate.id, FETCH_CANDIDATE_AND_MERGE));
          done = true;
        }
      });
    }
  }
});

const initialState = {
  candidates: null,
  pageNumber: 1,
  lastPage: false,
  totalMatches: 0,
  numberingStart: 0,
  numberingEnd: 0,
  selectedAnnotationSortOptions: null,
  annotationsInfo: null,
  filterFormData: null,
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
    case SET_CANDIDATES_ANNOTATION_SORT_OPTIONS: {
      return { ...state, selectedAnnotationSortOptions: action.item };
    }
    case FETCH_ANNOTATIONS_INFO_OK: {
      const annotationsInfo = action.data;
      return {
        ...state,
        annotationsInfo,
      };
    }
    case SET_CANDIDATES_FILTER_FORM_DATA: {
      const { formData } = action;
      return {
        ...state,
        filterFormData: formData,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("candidates", reducer);
