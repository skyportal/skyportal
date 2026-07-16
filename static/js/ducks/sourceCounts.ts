/**
 * Source counts widget data ("new sources in the last N days").
 *
 * RTK Query conversion of the old `FETCH_SOURCE_COUNTS` duck. The endpoint is
 * injected into the central `skyportalApi`. The old reducer wrapped the
 * response as `{ sourceCounts: data }`; here the query returns the payload
 * directly, so consumers read the count fields off the query `data`.
 *
 * The old websocket handler refetched on a `FETCH_SOURCE_COUNTS` message; here
 * we invalidate the "SourceCounts" tag so the active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface SourceCounts {
  count?: number | undefined;
  sinceDaysAgo?: number | undefined;
  [key: string]: unknown;
}

export const sourceCountsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSourceCounts: build.query<
      SourceCounts,
      { teamID?: number | null } | void
    >({
      query: (arg) =>
        arg && arg.teamID != null
          ? `api/internal/source_counts?teamID=${arg.teamID}`
          : "api/internal/source_counts",
      providesTags: ["SourceCounts"],
    }),
  }),
});

// Websocket: old handler refetched on FETCH_SOURCE_COUNTS.
invalidateOnMessage("skyportal/FETCH_SOURCE_COUNTS", () => ["SourceCounts"]);

export const { useGetSourceCountsQuery } = sourceCountsApi;
