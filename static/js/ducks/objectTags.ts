/**
 * Object tags: the list of available tag *options* (`objtagoption`) plus the
 * mutations that create/update/delete those options and that attach/detach a
 * tag to a specific object (`objtag`).
 *
 * RTK Query conversion of the old `objectTags` duck. The list query provides
 * the `ObjTagOption` tag; mutations on tag options invalidate it. Adding or
 * removing a tag on an object touches per-source tag state, so those mutations
 * invalidate `SourceTag`/`ObjTag` (consumers that read source slices still
 * refetch those manually where needed).
 *
 * The websocket `FETCH_TAG_OPTIONS` message is bridged to cache invalidation of
 * `ObjTagOption` via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface TagOption {
  id: number;
  name: string;
  color?: string | undefined;
  created_at?: string | undefined;
  [key: string]: unknown;
}

export const objectTagsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTagOptions: build.query<TagOption[], void>({
      query: () => "api/objtagoption",
      transformResponse: (data: TagOption[]) => data ?? [],
      providesTags: ["ObjTagOption"],
    }),
    createTagOption: build.mutation<TagOption, Record<string, unknown>>({
      query: (data) => ({
        url: "api/objtagoption",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["ObjTagOption"],
    }),
    updateTagOption: build.mutation<
      unknown,
      { id: number | string } & Record<string, unknown>
    >({
      query: (data) => ({
        url: `api/objtagoption/${data.id}`,
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: ["ObjTagOption"],
    }),
    deleteTagOption: build.mutation<
      unknown,
      { id: number | string } & Record<string, unknown>
    >({
      query: (data) => ({
        url: `api/objtagoption/${data.id}`,
        method: "DELETE",
        body: data,
      }),
      invalidatesTags: ["ObjTagOption", "ObjTag", "SourceTag"],
    }),
    addObjectTag: build.mutation<unknown, Record<string, unknown>>({
      query: (data) => ({
        url: "api/objtag",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["ObjTag", "SourceTag"],
    }),
    deleteObjectTag: build.mutation<
      unknown,
      { id: number | string } & Record<string, unknown>
    >({
      query: (data) => ({
        url: `api/objtag/${data.id}`,
        method: "DELETE",
        body: data,
      }),
      invalidatesTags: ["ObjTag", "SourceTag"],
    }),
  }),
});

// Websocket: old handler refetched the tag options on FETCH_TAG_OPTIONS.
invalidateOnMessage("skyportal/FETCH_TAG_OPTIONS", () => ["ObjTagOption"]);

export const {
  useGetTagOptionsQuery,
  useCreateTagOptionMutation,
  useUpdateTagOptionMutation,
  useDeleteTagOptionMutation,
  useAddObjectTagMutation,
  useDeleteObjectTagMutation,
} = objectTagsApi;
