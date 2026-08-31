import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
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
  created_at: string;
  title: string;
  description: string | null;
  link: string | null;
  user: CollaborationUser;
}

export const sourceInterestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
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

invalidateOnMessage("skyportal/REFRESH_SOURCE_INTERESTS", (payload) => [
  "SourceInterest",
  ...sourceTag(payload?.obj_id),
]);

export const {
  useGetSourceInterestsQuery,
  useSetSourceInterestMutation,
  useDeleteSourceInterestMutation,
} = sourceInterestsApi;
