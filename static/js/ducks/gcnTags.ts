/**
 * GCN event tags.
 *
 * RTK Query conversion of the old `FETCH_GCN_TAGS` duck. Websocket-driven
 * invalidation refetches the tag list; mutations post/delete a tag on an event.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface PostGcnTagArg {
  dateobs: string;
  text: string;
}

interface DeleteGcnTagArg {
  /** The event's dateobs: the delete route is keyed on it, not on an id. */
  dateobs: string;
  tag: string;
}

export const gcnTagsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed filter params
    // that the server ignored.
    getGcnTags: build.query<string[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchGcnEventTags()),
      providesTags: ["GcnTags"],
    }),
    postGcnTag: build.mutation<{ gcntag_id: number }, PostGcnTagArg>({
      queryFn: ({ dateobs, text }, api) =>
        clientQuery(api, (client) => client.postGcnEventTag(dateobs, text)),
      invalidatesTags: ["GcnTags"],
    }),
    deleteGcnTag: build.mutation<void, DeleteGcnTagArg>({
      queryFn: ({ dateobs, tag }, api) =>
        clientQuery(api, (client) => client.deleteGcnEventTag(dateobs, tag)),
      invalidatesTags: ["GcnTags"],
    }),
  }),
});

// Websocket: the old handler refetched the full tag list on FETCH_GCN_TAGS.
invalidateOnMessage("skyportal/FETCH_GCN_TAGS", () => ["GcnTags"]);

export const {
  useGetGcnTagsQuery,
  usePostGcnTagMutation,
  useDeleteGcnTagMutation,
} = gcnTagsApi;
