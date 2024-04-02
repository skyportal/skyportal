import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import * as candidateActions from "./candidate";
import store from "../store";

const FETCH_CANDIDATES = "skyportal/FETCH_CANDIDATES";
const FETCH_CANDIDATES_OK = "skyportal/FETCH_CANDIDATES_OK";

const FETCH_CANDIDATE_AND_MERGE = "skyportal/FETCH_CANDIDATE_AND_MERGE";
const FETCH_CANDIDATE_AND_MERGE_OK = "skyportal/FETCH_CANDIDATE_AND_MERGE_OK";

const FETCH_CANDIDATES_AND_APPEND = "skyportal/FETCH_CANDIDATES_AND_APPEND";
const FETCH_CANDIDATES_AND_APPEND_OK =
  "skyportal/FETCH_CANDIDATES_AND_APPEND_OK";

const REFRESH_CANDIDATE = "skyportal/REFRESH_CANDIDATE";

const SET_CANDIDATES_ANNOTATION_SORT_OPTIONS =
  "skyportal/SET_CANDIDATES_ANNOTATION_SORT_OPTIONS";

const FETCH_ANNOTATIONS_INFO = "skyportal/FETCH_ANNOTATIONS_INFO";
const FETCH_ANNOTATIONS_INFO_OK = "skyportal/FETCH_ANNOTATIONS_INFO_OK";

const SET_CANDIDATES_FILTER_FORM_DATA =
  "skyportal/SET_CANDIDATES_FILTER_FORM_DATA";

const GENERATE_PS1_THUMBNAIL = "skyportal/GENERATE_PS1_THUMBNAIL";
const GENERATE_PS1_THUMBNAILS = "skyportal/GENERATE_PS1_THUMBNAILS";

export const fetchCandidates = (filterParams = {}, append = false) => {
  if (!Object.keys(filterParams).includes("pageNumber")) {
    filterParams.pageNumber = 1;
  }
  return API.GET(
    "/api/candidates",
    append === false ? FETCH_CANDIDATES : FETCH_CANDIDATES_AND_APPEND,
    filterParams,
  );
};

export const generateSurveyThumbnail = (objID) =>
  API.POST("/api/internal/survey_thumbnail", GENERATE_PS1_THUMBNAIL, { objID });

export const generateSurveyThumbnails = (objIDs) =>
  API.POST("/api/internal/survey_thumbnail", GENERATE_PS1_THUMBNAILS, {
    objIDs,
  });

export const setCandidatesAnnotationSortOptions = (item) => ({
  type: SET_CANDIDATES_ANNOTATION_SORT_OPTIONS,
  item,
});

export const fetchAnnotationsInfo = () =>
  API.GET("/api/internal/annotations_info", FETCH_ANNOTATIONS_INFO);

export const setFilterFormData = (formData) => ({
  type: SET_CANDIDATES_FILTER_FORM_DATA,
  formData,
});

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
          dispatch(
            candidateActions.fetchCandidate(
              candidate.id,
              FETCH_CANDIDATE_AND_MERGE,
            ),
          );
          done = true;
        }
      });
    }
  }
});

const initialState = {
  candidates: null,
  pageNumber: 1,
  totalMatches: 0,
  selectedAnnotationSortOptions: null,
  annotationsInfo: null,
  filterFormData: null,
  queryID: null,
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_CANDIDATES_OK: {
      const { candidates, pageNumber, totalMatches, queryID } = action.data;
      return {
        ...state,
        candidates,
        pageNumber,
        totalMatches,
        queryID,
      };
    }
    case FETCH_CANDIDATE_AND_MERGE_OK: {
      const candidates = state.candidates?.map((candidate) =>
        candidate.id !== action.data.id ? candidate : action.data,
      );
      return { ...state, candidates };
    }
    case FETCH_CANDIDATES_AND_APPEND_OK: {
      const { candidates, pageNumber, totalMatches, queryID } = action.data;
      return {
        ...state,
        candidates: state.candidates.concat(candidates),
        pageNumber,
        totalMatches,
        queryID,
      };
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
