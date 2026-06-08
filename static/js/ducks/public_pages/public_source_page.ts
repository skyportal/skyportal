/**
 * Public source pages (version history for a source's public page).
 *
 * RTK Query conversion of the old `FETCH_PUBLIC_SOURCE_PAGES` duck. The list is
 * fetched per source id; generating and deleting a public page are mutations
 * that invalidate the list tag so it refetches.
 *
 * The websocket `REFRESH_PUBLIC_SOURCE_PAGES` message is bridged to cache
 * invalidation via `invalidateOnMessage`, preserving the old gate that only
 * refreshed when the pushed source matches the currently-loaded source.
 */
import { skyportalApi } from "../../api/skyportalApi";
import { invalidateOnMessage } from "../../api/wsInvalidation";

export const publicSourcePageApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    fetchPublicSourcePages: build.query({
      query: (sourceId) => `api/public_pages/source/${sourceId}`,
      // Tag per source id so a REFRESH_PUBLIC_SOURCE_PAGES message can invalidate
      // exactly the matching source's query (replaces the old global
      // `state.source.id === source_id` gate, which no longer exists).
      providesTags: (_result, _error, sourceId) => [
        { type: "FetchPublicSourcePages", id: sourceId },
      ],
    }),
    generatePublicSourcePage: build.mutation({
      query: ({ sourceId, payload }) => ({
        url: `api/public_pages/source/${sourceId}`,
        method: "POST",
        body: payload,
      }),
      invalidatesTags: ["FetchPublicSourcePages"],
    }),
    deletePublicSourcePage: build.mutation({
      query: (pageId) => ({
        url: `api/public_pages/source/${pageId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["FetchPublicSourcePages"],
    }),
  }),
});

// Websocket: old handler refetched pages only for the currently-loaded source.
invalidateOnMessage("skyportal/REFRESH_PUBLIC_SOURCE_PAGES", (payload) => {
  const { source_id } = payload;
  return [{ type: "FetchPublicSourcePages", id: source_id }];
});

export const {
  useFetchPublicSourcePagesQuery,
  useGeneratePublicSourcePageMutation,
  useDeletePublicSourcePageMutation,
} = publicSourcePageApi;
