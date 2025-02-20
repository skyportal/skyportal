import messageHandler from "baselayer/MessageHandler";

import * as API from "../../API";
import store from "../../store";

const FETCH_CANDIDATE_SCAN_REPORT = "skyportal/FETCH_CANDIDATE_SCAN_REPORT";
const FETCH_CANDIDATE_SCAN_REPORT_OK =
  "skyportal/FETCH_CANDIDATE_SCAN_REPORT_OK";
const GENERATE_CANDIDATE_SCAN_REPORT =
  "skyportal/GENERATE_CANDIDATE_SCAN_REPORT";
const UPDATE_CANDIDATE_FROM_REPORT = "skyportal/UPDATE_CANDIDATE_FROM_REPORT";

const REFRESH_CANDIDATE_SCAN_REPORT = "skyportal/REFRESH_CANDIDATE_SCAN_REPORT";

export const fetchCandidatesScanReport = (params) =>
  API.GET(`/api/candidates/scan_report`, FETCH_CANDIDATE_SCAN_REPORT, params);

export const generateCandidateScanReport = (payload) =>
  API.POST(
    `/api/candidates/scan_report`,
    GENERATE_CANDIDATE_SCAN_REPORT,
    payload,
  );

export const updateCandidateFromReport = (candidateFromReportId, payload) =>
  API.PATCH(
    `/api/candidates/scan_report/${candidateFromReportId}`,
    UPDATE_CANDIDATE_FROM_REPORT,
    payload,
  );

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_CANDIDATE_SCAN_REPORT) {
    dispatch(fetchCandidatesScanReport({}));
  }
});

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_CANDIDATE_SCAN_REPORT_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("candidatesScanReport", reducer);
