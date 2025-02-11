import * as API from "../../API";

const SUBMIT_CANDIDATE_TO_REPORT = "skyportal/SUBMIT_CANDIDATE_TO_REPORT";
const UPDATE_CANDIDATE_FROM_REPORT = "skyportal/UPDATE_CANDIDATE_FROM_REPORT";
const FETCH_CANDIDATE_SCAN_REPORT = "skyportal/FETCH_CANDIDATE_SCAN_REPORT";

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
