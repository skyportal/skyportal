/**
 * Top sources (the "Top Sources" widget).
 *
 * RTK Query conversion of the old `FETCH_TOP_SOURCES` duck. The endpoint is
 * injected into the central `skyportalApi` and returns the list of source views
 * consumers render. The old websocket handler refetched on a FETCH_TOP_SOURCES
 * message; here we invalidate the "SourceView" tag so the active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const topSourcesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTopSources: build.query<any[], void>({
      query: () => "api/internal/source_views",
      providesTags: ["SourceView"],
    }),
  }),
});

// Websocket: old handler refetched top sources on FETCH_TOP_SOURCES.
invalidateOnMessage("skyportal/FETCH_TOP_SOURCES", () => ["SourceView"]);

export const { useGetTopSourcesQuery } = topSourcesApi;
