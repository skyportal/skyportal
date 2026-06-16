/**
 * Scan report items.
 *
 * RTK Query conversion of the old `FETCH_SCAN_REPORT_ITEM` /
 * `UPDATE_SCAN_REPORT_ITEM` duck. The endpoints are injected into the central
 * `skyportalApi`; the websocket `REFRESH_SCAN_REPORT_ITEM` message is bridged to
 * cache invalidation via `invalidateOnMessage`, preserving the old conditional
 * logic that only refreshed when the pushed `report_id` matched the currently
 * loaded report.
 */
import { skyportalApi } from "../../api/skyportalApi";
import { invalidateOnMessage } from "../../api/wsInvalidation";
import type { RootState } from "../../types/store";
import type { RouteData } from "../../types/routeSchemaMap";

export const scanReportItemApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getScanReportItems: build.query<
      RouteData<"GET /api/candidates/scan_reports/{report_id}/items/{_}">,
      number
    >({
      query: (reportId) => `api/candidates/scan_reports/${reportId}/items`,
      providesTags: ["ScanReportItem"],
    }),
    updateScanReportItem: build.mutation<
      RouteData<"PATCH /api/candidates/scan_reports/{report_id}/items/{item_id}">,
      { reportId: number; itemId: number; payload: Record<string, unknown> }
    >({
      query: ({ reportId, itemId, payload }) => ({
        url: `api/candidates/scan_reports/${reportId}/items/${itemId}`,
        method: "PATCH",
        body: payload,
      }),
      invalidatesTags: ["ScanReportItem"],
    }),
  }),
});

export const { useGetScanReportItemsQuery, useUpdateScanReportItemMutation } =
  scanReportItemApi;

invalidateOnMessage(
  "skyportal/REFRESH_SCAN_REPORT_ITEM",
  (payload, getState) => {
    const { report_id } = payload;
    const items = scanReportItemApi.endpoints.getScanReportItems.select(
      Number(report_id),
    )(getState() as RootState).data;
    if (
      items?.length &&
      Number(report_id) === Number(items[0]?.scan_report_id)
    ) {
      return ["ScanReportItem"];
    }
    return null;
  },
);
