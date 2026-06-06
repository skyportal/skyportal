/**
 * Recent sources widget data.
 *
 * RTK Query conversion of the old `FETCH_RECENT_SOURCES` duck. The endpoint is
 * injected into the central `skyportalApi`. The old websocket handler refetched
 * recent sources on a FETCH_RECENT_SOURCES message; here we invalidate the
 * "RecentSource" tag so the active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type RecentSource = Record<string, any>;

export const recentSourcesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getRecentSources: build.query<RecentSource[], void>({
      query: () => "api/internal/recent_sources",
      providesTags: ["RecentSource"],
    }),
  }),
});

// Websocket: old handler refetched recent sources on FETCH_RECENT_SOURCES.
invalidateOnMessage("skyportal/FETCH_RECENT_SOURCES", () => ["RecentSource"]);

export const { useGetRecentSourcesQuery } = recentSourcesApi;
