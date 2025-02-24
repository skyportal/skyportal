import messageHandler from "baselayer/MessageHandler";

import * as API from "../../API";
import store from "../../store";

const FETCH_SCAN_REPORTS = "skyportal/FETCH_SCAN_REPORTS";
const FETCH_SCAN_REPORTS_OK = "skyportal/FETCH_SCAN_REPORTS_OK";
const GENERATE_SCAN_REPORT = "skyportal/GENERATE_SCAN_REPORT";
const REFRESH_SCAN_REPORTS = "skyportal/REFRESH_SCAN_REPORTS";

export const fetchScanReports = (params) =>
  API.GET(`/api/candidates/scan_reports`, FETCH_SCAN_REPORTS, params);

export const generateScanReport = (payload) =>
  API.POST(`/api/candidates/scan_reports`, GENERATE_SCAN_REPORT, payload);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_SCAN_REPORTS) {
    dispatch(fetchScanReports({}));
  }
});

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_SCAN_REPORTS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("scanReports", reducer);
