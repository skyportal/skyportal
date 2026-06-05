/**
 * Candidate scanning reports.
 *
 * RTK Query conversion of the old `FETCH_SCAN_REPORTS` duck. The list query
 * accepts pagination params; generating a report is a mutation that invalidates
 * the `ScanReport` tag so the list refetches. The websocket
 * `REFRESH_SCAN_REPORTS` message is bridged to cache invalidation.
 */
import { skyportalApi } from "../../api/skyportalApi";
import { invalidateOnMessage } from "../../api/wsInvalidation";

export const scanReportsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getScanReports: build.query({
      query: (params) => {
        const queryString = new URLSearchParams(params ?? {}).toString();
        return queryString
          ? `api/candidates/scan_reports?${queryString}`
          : "api/candidates/scan_reports";
      },
      providesTags: ["ScanReport"],
    }),
    generateScanReport: build.mutation({
      query: (payload) => ({
        url: "api/candidates/scan_reports",
        method: "POST",
        body: payload,
      }),
      invalidatesTags: ["ScanReport"],
    }),
  }),
});

// Websocket: the old handler refetched the report list on REFRESH_SCAN_REPORTS.
invalidateOnMessage("skyportal/REFRESH_SCAN_REPORTS", () => ["ScanReport"]);

export const { useGetScanReportsQuery, useGenerateScanReportMutation } =
  scanReportsApi;
