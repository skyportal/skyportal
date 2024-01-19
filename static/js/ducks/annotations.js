import * as API from "../API";
import store from "../store";

const FETCH_ANNOTATIONS_INFO = "skyportal/FETCH_ANNOTATIONS_INFO";
const FETCH_ANNOTATIONS_INFO_OK = "skyportal/FETCH_ANNOTATIONS_INFO_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchAnnotationsInfo = (filterParams = {}) =>
  API.GET(
    "/api/internal/annotations_info",
    FETCH_ANNOTATIONS_INFO,
    filterParams,
  );

const initialState = {};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_ANNOTATIONS_INFO_OK: {
      const annotationsInfo = action.data;
      return {
        ...state,
        annotationsInfo,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("annotationsInfo", reducer);
