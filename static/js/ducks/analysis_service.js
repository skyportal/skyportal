import * as API from "../API";
import store from "../store";

const FETCH_ANALYSIS_SERVICE = "skyportal/FETCH_ANALYSIS_SERVICE";
const FETCH_ANALYSIS_SERVICE_OK = "skyportal/FETCH_ANALYSIS_SERVICE_OK";

const SUBMIT_ANALYSIS_SERVICE = "skyportal/SUBMIT_ANALYSIS_SERVICE";

const MODIFY_ANALYSIS_SERVICE = "skyportal/MODIFY_ANALYSIS_SERVICE";

export const fetchAnalysisService = (id) =>
  API.GET(`/api/analysis_service/${id}`, FETCH_ANALYSIS_SERVICE);

export const submitAnalysisService = (run) =>
  API.POST(`/api/analysis_service`, SUBMIT_ANALYSIS_SERVICE, run);

export const modifyAnalysisService = (id, params) =>
  API.PUT(`/api/analysis_service/${id}`, MODIFY_ANALYSIS_SERVICE, params);

const reducer = (state = { assignments: [] }, action) => {
  switch (action.type) {
    case FETCH_ANALYSIS_SERVICE_OK: {
      const analysis_service = action.data;
      return {
        ...state,
        ...analysis_service,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("analysis_service", reducer);
