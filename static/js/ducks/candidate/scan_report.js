import * as API from "../../API";
import store from "../../store";
import messageHandler from "../../../../baselayer/static/js/MessageHandler";

const FETCH_SCAN_REPORT_ITEM = "skyportal/FETCH_SCAN_REPORT_ITEM";
const FETCH_SCAN_REPORT_ITEM_OK = "skyportal/FETCH_SCAN_REPORT_ITEM_OK";
const UPDATE_SCAN_REPORT_ITEM = "skyportal/UPDATE_SCAN_REPORT_ITEM";
const REFRESH_SCAN_REPORT_ITEM = "skyportal/REFRESH_SCAN_REPORT_ITEM";

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

messageHandler.add((actionType, payload, dispatch, getState) => {
  if (actionType === REFRESH_SCAN_REPORT_ITEM) {
    const { report_id } = payload;
    if (
      getState().scanReportItems?.length &&
      Number(report_id) === Number(getState().scanReportItems[0].scan_report_id)
    ) {
      dispatch(fetchScanReportItem(report_id));
    }
  }
});

const reducer = (state = [], action) => {
  switch (action.type) {
    case FETCH_SCAN_REPORT_ITEM_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("scanReportItems", reducer);
