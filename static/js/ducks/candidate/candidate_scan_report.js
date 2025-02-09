import * as API from "../../API";

const SAVE_SCAN_TO_REPORT = "skyportal/SAVE_SCAN_TO_REPORT";
const FETCH_SCAN_REPORT = "skyportal/FETCH_SCAN_REPORT";
const DELETE_SCAN_FROM_REPORT = "skyportal/DELETE_SCAN_FROM_REPORT";

export const saveScanToReport = (payload) =>
  API.POST(`/api/candidates/scan_report`, SAVE_SCAN_TO_REPORT, payload);

export const fetchScanReport = (params) =>
  API.GET(`/api/candidates/scan_report`, FETCH_SCAN_REPORT, params);

export const deleteScanFromReport = (scanId) =>
  API.DELETE(`/api/candidates/scan_report/${scanId}`, DELETE_SCAN_FROM_REPORT);
