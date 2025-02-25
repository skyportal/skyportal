import * as API from "../../API";

const FETCH_SCAN_REPORT_ITEM = "skyportal/FETCH_SCAN_REPORT_ITEM";
const UPDATE_SCAN_REPORT_ITEM = "skyportal/UPDATE_SCAN_REPORT_ITEM";

export const fetchScanReportItem = (reportId) =>
  API.GET(
    `/api/candidates/scan_reports/${reportId}/items`,
    FETCH_SCAN_REPORT_ITEM,
  );

export const updateScanReportItem = (reportId, itemId, payload) =>
  API.PATCH(
    `/api/candidates/scan_reports/${reportId}/items/${itemId}`,
    UPDATE_SCAN_REPORT_ITEM,
    payload,
  );
