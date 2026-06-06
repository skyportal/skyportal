/**
 * Recent GCN events for the home-page widget.
 *
 * RTK Query conversion of the old `FETCH_RECENT_GCNEVENTS` duck. The old
 * websocket handler refetched on a REFRESH_RECENT_GCNEVENTS message; here we
 * invalidate the "RecentGcnEvent" tag so the active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type RecentGcnEvent = Record<string, any>;

export const recentGcnEventsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getRecentGcnEvents: build.query<RecentGcnEvent[], void>({
      query: () => "api/internal/recent_gcn_events",
      providesTags: ["RecentGcnEvent"],
    }),
  }),
});

// Websocket: old handler refetched on REFRESH_RECENT_GCNEVENTS.
invalidateOnMessage("skyportal/REFRESH_RECENT_GCNEVENTS", () => [
  "RecentGcnEvent",
]);

export const { useGetRecentGcnEventsQuery } = recentGcnEventsApi;
