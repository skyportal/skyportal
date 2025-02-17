import messageHandler from "baselayer/MessageHandler";

import * as API from "../../API";
import store from "../../store";

const FETCH_CANDIDATE_SCAN_REPORT = "skyportal/FETCH_CANDIDATE_SCAN_REPORT";
const FETCH_CANDIDATE_SCAN_REPORT_OK =
  "skyportal/FETCH_CANDIDATE_SCAN_REPORT_OK";
const SUBMIT_CANDIDATE_TO_REPORT = "skyportal/SUBMIT_CANDIDATE_TO_REPORT";
const UPDATE_CANDIDATE_FROM_REPORT = "skyportal/UPDATE_CANDIDATE_FROM_REPORT";

const REFRESH_CANDIDATE_SCAN_REPORT = "skyportal/REFRESH_CANDIDATE_SCAN_REPORT";

export const submitCandidateToReport = (payload) =>
  API.POST(`/api/candidates/scan_report`, SUBMIT_CANDIDATE_TO_REPORT, payload);

export const updateCandidateFromReport = (candidateFromReportId, payload) =>
  API.PATCH(
    `/api/candidates/scan_report/${candidateFromReportId}`,
    UPDATE_CANDIDATE_FROM_REPORT,
    payload,
  );

export const fetchCandidatesScanReport = (params) =>
  API.GET(`/api/candidates/scan_report`, FETCH_CANDIDATE_SCAN_REPORT, params);

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
