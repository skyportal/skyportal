import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_ANALYSIS_SERVICES_LIST = "skyportal/FETCH_ANALYSIS_SERVICES_LIST";
const FETCH_ANALYSIS_SERVICES_LIST_OK =
  "skyportal/FETCH_ANALYSIS_SERVICES_LIST_OK";

const REFRESH_ANALYSIS_SERVICES = "skyportal/REFRESH_ANALYSIS_SERVICES";

const FETCH_ANALYSIS_SERVICE = "skyportal/FETCH_ANALYSIS_SERVICE";
const FETCH_ANALYSIS_SERVICE_OK = "skyportal/FETCH_ANALYSIS_SERVICE_OK";

const SUBMIT_ANALYSIS_SERVICE = "skyportal/SUBMIT_ANALYSIS_SERVICE";

const MODIFY_ANALYSIS_SERVICE = "skyportal/MODIFY_ANALYSIS_SERVICE";

const DELETE_ANALYSIS_SERVICE = "skyportal/DELETE_ANALYSIS_SERVICE";

export const fetchAnalysisServices = (params = {}) =>
  API.GET("/api/analysis_service", FETCH_ANALYSIS_SERVICES_LIST, params);

export const fetchAnalysisService = (id) =>
  API.GET(`/api/analysis_service/${id}`, FETCH_ANALYSIS_SERVICE);

export const submitAnalysisService = (run) =>
  API.POST(`/api/analysis_service`, SUBMIT_ANALYSIS_SERVICE, run);

export const modifyAnalysisService = (id, params) =>
  API.PUT(`/api/analysis_service/${id}`, MODIFY_ANALYSIS_SERVICE, params);

export const deleteAnalysisService = (id) =>
  API.DELETE(`/api/analysis_service/${id}`, DELETE_ANALYSIS_SERVICE);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_ANALYSIS_SERVICES) {
    dispatch(fetchAnalysisServices());
  }
});

const reducer_service = (state = {}, action) => {
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

const reducer_services = (state = { analysisServiceList: [] }, action) => {
  switch (action.type) {
    case FETCH_ANALYSIS_SERVICES_LIST_OK: {
      const analysisServiceList = action.data;
      return {
        ...state,
        analysisServiceList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("analysis_service", reducer_service);
store.injectReducer("analysis_services", reducer_services);
