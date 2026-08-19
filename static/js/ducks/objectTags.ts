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
import type { ObjTagOption, ObjTagPostResponse } from "skyportal-js/Tags";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const objectTagsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTagOptions: build.query<ObjTagOption[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchObjTagOptions()),
      providesTags: ["ObjTagOption"],
    }),
    createTagOption: build.mutation<
      ObjTagOption,
      { name: string; color?: string }
    >({
      queryFn: ({ name, color }, api) =>
        clientQuery(api, (client) => client.postObjTagOption(name, { color })),
      invalidatesTags: ["ObjTagOption"],
    }),
    updateTagOption: build.mutation<
      void,
      { id: number | string; name: string; color?: string }
    >({
      queryFn: ({ id, name, color }, api) =>
        clientQuery(api, (client) =>
          client.updateObjTagOption(Number(id), name, { color }),
        ),
      invalidatesTags: ["ObjTagOption"],
    }),
    deleteTagOption: build.mutation<void, { id: number | string }>({
      queryFn: ({ id }, api) =>
        clientQuery(api, (client) => client.deleteObjTagOption(Number(id))),
      invalidatesTags: ["ObjTagOption", "ObjTag", "SourceTag"],
    }),
    addObjectTag: build.mutation<
      ObjTagPostResponse,
      { obj_id: string; objtagoption_id: number; group_ids?: number[] }
    >({
      queryFn: ({ obj_id, objtagoption_id, group_ids }, api) =>
        clientQuery(api, (client) =>
          client.postObjTag(obj_id, objtagoption_id, { groupIds: group_ids }),
        ),
      invalidatesTags: ["ObjTag", "SourceTag"],
    }),
    deleteObjectTag: build.mutation<
      void,
      { id: number | string; group_ids?: number[] }
    >({
      queryFn: ({ id, group_ids }, api) =>
        clientQuery(api, (client) =>
          client.deleteObjTag(Number(id), { groupIds: group_ids }),
        ),
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
