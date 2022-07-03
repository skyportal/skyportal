import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_ANALYSIS_SERVICES = "skyportal/FETCH_ANALYSIS_SERVICES";
const FETCH_ANALYSIS_SERVICES_OK = "skyportal/FETCH_ANALYSIS_SERVICES_OK";

const REFRESH_ANALYSIS_SERVICES = "skyportal/REFRESH_ANALYSIS_SERVICES";

// eslint-disable-next-line import/prefer-default-export
export const fetchAnalysisServices = (params = {}) =>
  API.GET("/api/analysis_service", FETCH_ANALYSIS_SERVICES, params);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_ANALYSIS_SERVICES) {
    dispatch(fetchAnalysisServices());
  }
});

const reducer = (state = { analysisServiceList: [] }, action) => {
  switch (action.type) {
    case FETCH_ANALYSIS_SERVICES_OK: {
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

store.injectReducer("analysis_services", reducer);
