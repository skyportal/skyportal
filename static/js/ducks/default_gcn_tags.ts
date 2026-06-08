/**
 * Default GCN tags.
 *
 * RTK Query conversion of the old `FETCH_DEFAULT_GCN_TAGS` duck. Endpoints are
 * injected into the central `skyportalApi`. The list query provides the
 * `FetchDefaultGcnTags` tag; submit/delete mutations invalidate it so the list
 * refetches.
 *
 * The websocket `REFRESH_DEFAULT_GCN_TAGS` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface DefaultGcnTag {
  id: number;
  default_tag_name: string;
  filters?: Record<string, unknown> | undefined;
  [key: string]: unknown;
}

export const defaultGcnTagsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultGcnTags: build.query<DefaultGcnTag[], void>({
      query: () => "api/default_gcn_tag",
      providesTags: ["FetchDefaultGcnTags"],
    }),
    submitDefaultGcnTag: build.mutation<unknown, Record<string, unknown>>({
      query: (default_tag) => ({
        url: "api/default_gcn_tag",
        method: "POST",
        body: default_tag,
      }),
      invalidatesTags: ["FetchDefaultGcnTags"],
    }),
    deleteDefaultGcnTag: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/default_gcn_tag/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["FetchDefaultGcnTags"],
    }),
  }),
});

// Websocket-driven invalidation: refresh on REFRESH_DEFAULT_GCN_TAGS.
invalidateOnMessage("skyportal/REFRESH_DEFAULT_GCN_TAGS", () => [
  "FetchDefaultGcnTags",
]);

export const {
  useGetDefaultGcnTagsQuery,
  useSubmitDefaultGcnTagMutation,
  useDeleteDefaultGcnTagMutation,
} = defaultGcnTagsApi;
