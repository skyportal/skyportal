import messageHandler from "baselayer/MessageHandler";

import * as API from "../../API";
import store from "../../store";

const FETCH_CANDIDATE_SCAN_REPORTS = "skyportal/FETCH_CANDIDATE_SCAN_REPORTS";
const FETCH_CANDIDATE_SCAN_REPORTS_OK =
  "skyportal/FETCH_CANDIDATE_SCAN_REPORTS_OK";
const GENERATE_CANDIDATE_SCAN_REPORT =
  "skyportal/GENERATE_CANDIDATE_SCAN_REPORT";
const UPDATE_CANDIDATE_FROM_REPORT = "skyportal/UPDATE_CANDIDATE_FROM_REPORT";

const REFRESH_CANDIDATE_SCAN_REPORT = "skyportal/REFRESH_CANDIDATE_SCAN_REPORT";

export const fetchCandidatesScanReports = (params) =>
  API.GET(`/api/candidates/scan_reports`, FETCH_CANDIDATE_SCAN_REPORTS, params);

export const generateCandidateScanReport = (payload) =>
  API.POST(
    `/api/candidates/scan_reports`,
    GENERATE_CANDIDATE_SCAN_REPORT,
    payload,
  );

export const updateCandidateFromReport = (candidateFromReportId, payload) =>
  API.PATCH(
    `/api/candidates/scan_reports/${candidateFromReportId}`,
    UPDATE_CANDIDATE_FROM_REPORT,
    payload,
  );

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_CANDIDATE_SCAN_REPORT) {
    dispatch(fetchCandidatesScanReports({}));
  }
});

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_CANDIDATE_SCAN_REPORTS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("candidatesScanReports", reducer);
