import * as API from "../../API";

const SUBMIT_CANDIDATE_TO_REPORT = "skyportal/SUBMIT_CANDIDATE_TO_REPORT";
const FETCH_CANDIDATE_SCAN_REPORT = "skyportal/FETCH_CANDIDATE_SCAN_REPORT";
const DELETE_CANDIDATE_FROM_REPORT = "skyportal/DELETE_CANDIDATE_FROM_REPORT";

export const submitCandidateToReport = (candidateId, payload) =>
  API.POST(
    `/api/candidates/scan_report/${candidateId}`,
    SUBMIT_CANDIDATE_TO_REPORT,
    payload,
  );

export const fetchCandidatesScanReport = (params) =>
  API.GET(`/api/candidates/scan_report`, FETCH_CANDIDATE_SCAN_REPORT, params);

export const deleteCandidateFromReport = (scanId) =>
  API.DELETE(
    `/api/candidates/scan_report/${scanId}`,
    DELETE_CANDIDATE_FROM_REPORT,
  );
