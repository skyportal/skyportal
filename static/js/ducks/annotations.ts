import * as API from "../API";
import store from "../store";

const FETCH_ANNOTATIONS_INFO = "skyportal/FETCH_ANNOTATIONS_INFO";
const FETCH_ANNOTATIONS_INFO_OK = "skyportal/FETCH_ANNOTATIONS_INFO_OK";

export const fetchAnnotationsInfo = (filterParams: Record<string, any> = {}) =>
  API.GET(
    "/api/internal/annotations_info",
    FETCH_ANNOTATIONS_INFO,
    filterParams,
  );

const initialState: Record<string, any> = {};

const reducer = (
  state: Record<string, any> = initialState,
  action: { type: string; data?: any },
): Record<string, any> => {
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
