import * as API from "../../API";

const SUBMIT_CANDIDATE_TO_REPORT = "skyportal/SUBMIT_CANDIDATE_TO_REPORT";
const FETCH_SCAN_REPORT = "skyportal/FETCH_SCAN_REPORT";
const DELETE_CANDIDATE_FROM_REPORT = "skyportal/DELETE_CANDIDATE_FROM_REPORT";

export const submitCandidateToReport = (scanId, payload) =>
  API.POST(`/api/candidates/scan_report`, SUBMIT_CANDIDATE_TO_REPORT, payload);

export const fetchScanReport = (params) =>
  API.GET(`/api/candidates/scan_report`, FETCH_SCAN_REPORT, params);

export const deleteCandidateFromReport = (scanId) =>
  API.DELETE(
    `/api/candidates/scan_report/${scanId}`,
    DELETE_CANDIDATE_FROM_REPORT,
  );
