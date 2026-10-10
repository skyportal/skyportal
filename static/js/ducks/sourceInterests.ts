import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage, findCachedQueryArg } from "../api/wsInvalidation";
import { sourceTag } from "./sourceTags";

export interface CollaborationUser {
  id?: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
  gravatar_url: string;
  is_bot: boolean;
}

export interface SourceInterest {
  id: number;
  obj_id: string;
  created_at: string;
  title: string;
  description: string | null;
  link: string | null;
  user: CollaborationUser;
}

export const sourceInterestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAllSourceInterests: build.query<SourceInterest[], void>({
      query: () => "api/source_interests",
      providesTags: ["SourceInterest"],
    }),
    getSourceInterests: build.query<SourceInterest[], string>({
      query: (obj_id) => `api/sources/${obj_id}/interests`,
      providesTags: ["SourceInterest"],
    }),
    setSourceInterest: build.mutation<
      { id: number },
      { obj_id: string } & Record<string, unknown>
    >({
      query: ({ obj_id, ...body }) => ({
        url: `api/sources/${obj_id}/interests`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { obj_id }) => [
        "SourceInterest",
        ...sourceTag(obj_id),
      ],
    }),
    deleteSourceInterest: build.mutation<
      unknown,
      { obj_id: string; interest_id: number }
    >({
      query: ({ obj_id, interest_id }) => ({
        url: `api/sources/${obj_id}/interests/${interest_id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { obj_id }) => [
        "SourceInterest",
        ...sourceTag(obj_id),
      ],
    }),
  }),
});

// Broadcast to every client, so it carries the source's internal_key rather
// than its id: translate it to the id of a cached source.
invalidateOnMessage(
  "skyportal/REFRESH_SOURCE_INTERESTS",
  (payload, getState) => {
    const objKey = payload?.obj_key as string | undefined;
    if (!objKey) {
      return ["SourceInterest"];
    }
    const objId = findCachedQueryArg(
      getState,
      "getSource",
      (data) => data?.internal_key === objKey,
    ) as string | number | null;
    return ["SourceInterest", ...(objId != null ? sourceTag(objId) : [])];
  },
);

export const {
  useGetAllSourceInterestsQuery,
  useGetSourceInterestsQuery,
  useSetSourceInterestMutation,
  useDeleteSourceInterestMutation,
} = sourceInterestsApi;
