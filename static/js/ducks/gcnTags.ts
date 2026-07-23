/**
 * GCN event tags.
 *
 * RTK Query conversion of the old `FETCH_GCN_TAGS` duck. Websocket-driven
 * invalidation refetches the tag list; mutations post/delete a tag on an event.
 */
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface PostGcnTagArg {
  dateobs: string;
  text: string;
}

interface DeleteGcnTagArg {
  gcnEventID: number | string;
  tag: string;
}

export const gcnTagsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGcnTags: build.query<string[], Record<string, unknown> | void>({
      query: (filterParams) => {
        const params = buildQueryString(
          (filterParams as Record<string, string>) ?? {},
        );
        return params ? `api/gcn_event/tags?${params}` : "api/gcn_event/tags";
      },
      providesTags: ["GcnTags"],
    }),
    postGcnTag: build.mutation<unknown, PostGcnTagArg>({
      query: (data) => ({
        url: "api/gcn_event/tags",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["GcnTags"],
    }),
    deleteGcnTag: build.mutation<unknown, DeleteGcnTagArg>({
      query: ({ gcnEventID, tag }) => ({
        url: `api/gcn_event/tags/${gcnEventID}`,
        method: "DELETE",
        body: { tag },
      }),
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
