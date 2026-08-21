/**
 * Candidate scanning reports.
 *
 * RTK Query conversion of the old `FETCH_SCAN_REPORTS` duck. The list query
 * accepts pagination params; generating a report is a mutation that invalidates
 * the `ScanReport` tag so the list refetches. The websocket
 * `REFRESH_SCAN_REPORTS` message is bridged to cache invalidation.
 */
import type {
  FetchScanReportsOptions,
  ScanReportPost,
  ScanReportsPage,
} from "skyportal-js/Candidates";

import { skyportalApi } from "../../api/skyportalApi";
import { clientQuery } from "../../api/skyportalClient";
import { invalidateOnMessage } from "../../api/wsInvalidation";

export const scanReportsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getScanReports: build.query<
      ScanReportsPage,
      FetchScanReportsOptions | undefined
    >({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.fetchScanReports(params ?? {})),
      providesTags: ["ScanReport"],
    }),
    generateScanReport: build.mutation<void, ScanReportPost>({
      queryFn: (payload, api) =>
        clientQuery(api, (client) => client.postScanReport(payload)),
      invalidatesTags: ["ScanReport"],
    }),
  }),
});

// Websocket: the old handler refetched the report list on REFRESH_SCAN_REPORTS.
invalidateOnMessage("skyportal/REFRESH_SCAN_REPORTS", () => ["ScanReport"]);

export const { useGetScanReportsQuery, useGenerateScanReportMutation } =
  scanReportsApi;
