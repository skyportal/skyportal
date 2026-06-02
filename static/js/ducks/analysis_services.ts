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

export const fetchAnalysisServices = (params: Record<string, any> = {}) =>
  API.GET("/api/analysis_service", FETCH_ANALYSIS_SERVICES_LIST, params);

export const fetchAnalysisService = (id: number | string) =>
  API.GET(`/api/analysis_service/${id}`, FETCH_ANALYSIS_SERVICE);

export const submitAnalysisService = (run: any) =>
  API.POST(`/api/analysis_service`, SUBMIT_ANALYSIS_SERVICE, run);

export const modifyAnalysisService = (id: number | string, params: any) =>
  API.PUT(`/api/analysis_service/${id}`, MODIFY_ANALYSIS_SERVICE, params);

export const deleteAnalysisService = (id: number | string) =>
  API.DELETE(`/api/analysis_service/${id}`, DELETE_ANALYSIS_SERVICE);

messageHandler.add((actionType: string, _payload: any, dispatch: any) => {
  if (actionType === REFRESH_ANALYSIS_SERVICES) {
    dispatch(fetchAnalysisServices());
  }
});

interface AnalysisServiceAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer_service = (
  state: Record<string, any> = {},
  action: AnalysisServiceAction,
) => {
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

const reducer_services = (
  state: Record<string, any> = { analysisServiceList: [] },
  action: AnalysisServiceAction,
) => {
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
