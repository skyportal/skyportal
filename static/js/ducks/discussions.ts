import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { components } from "../types/api";

export type Discussion = components["schemas"]["DiscussionResponse"];
export type DiscussionMessage =
  components["schemas"]["DiscussionMessageResponse"];
export type DiscussionMessagePage =
  components["schemas"]["DiscussionMessageListResponse"];
export type DiscussionUser = components["schemas"]["DiscussionUserResponse"];
export type CommentThread = components["schemas"]["CommentThreadResponse"];

const LIST = { type: "Discussions" as const, id: "LIST" };
const messagesTag = (id: number) => ({ type: "Discussions" as const, id });
const membersTag = (id: number) => ({
  type: "Discussions" as const,
  id: `members:${id}`,
});

export const discussionsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDiscussions: build.query<Discussion[], void>({
      query: () => "api/discussions",
      transformResponse: (data: { discussions: Discussion[] }) =>
        data.discussions,
      providesTags: [LIST],
    }),
    getDiscussionMessages: build.infiniteQuery<
      DiscussionMessagePage,
      number,
      number | null
    >({
      infiniteQueryOptions: {
        initialPageParam: null,
        getNextPageParam: (lastPage) =>
          lastPage.has_more ? lastPage.messages?.[0]?.id : undefined,
      },
      query: ({ queryArg, pageParam }) =>
        `api/discussions/${queryArg}/messages${pageParam ? `?before=${pageParam}` : ""}`,
      providesTags: (_result, _error, id) => [messagesTag(id)],
    }),
    getDiscussionMembers: build.query<DiscussionUser[], number>({
      query: (id) => `api/discussions/${id}/members`,
      transformResponse: (data: { members: DiscussionUser[] }) => data.members,
      providesTags: (_result, _error, id) => [membersTag(id)],
    }),
    getCommentThreads: build.query<CommentThread[], void>({
      query: () => "api/comment_threads",
      transformResponse: (data: { threads: CommentThread[] }) => data.threads,
      providesTags: ["CommentThreads"],
    }),
    startDiscussion: build.mutation<
      { id: number },
      {
        direct?: boolean | undefined;
        user_ids?: number[] | undefined;
        group_id?: number | undefined;
        name?: string | undefined;
      }
    >({
      query: (body) => ({ url: "api/discussions", method: "POST", body }),
      invalidatesTags: [LIST],
    }),
    renameDiscussion: build.mutation<unknown, { id: number; name: string }>({
      query: ({ id, name }) => ({
        url: `api/discussions/${id}`,
        method: "PATCH",
        body: { name },
      }),
      invalidatesTags: [LIST],
    }),
    deleteDiscussion: build.mutation<unknown, number>({
      query: (id) => ({ url: `api/discussions/${id}`, method: "DELETE" }),
      invalidatesTags: [LIST],
    }),
    sendDiscussionMessage: build.mutation<
      { id: number },
      { id: number; text: string }
    >({
      query: ({ id, text }) => ({
        url: `api/discussions/${id}/messages`,
        method: "POST",
        body: { text },
      }),
      invalidatesTags: (_result, _error, { id }) => [LIST, messagesTag(id)],
    }),
    editDiscussionMessage: build.mutation<
      unknown,
      { id: number; messageId: number; text: string }
    >({
      query: ({ id, messageId, text }) => ({
        url: `api/discussions/${id}/messages/${messageId}`,
        method: "PATCH",
        body: { text },
      }),
      invalidatesTags: (_result, _error, { id }) => [LIST, messagesTag(id)],
    }),
    deleteDiscussionMessage: build.mutation<
      unknown,
      { id: number; messageId: number }
    >({
      query: ({ id, messageId }) => ({
        url: `api/discussions/${id}/messages/${messageId}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { id }) => [LIST, messagesTag(id)],
    }),
    addDiscussionMembers: build.mutation<
      unknown,
      { id: number; user_ids: number[] }
    >({
      query: ({ id, user_ids }) => ({
        url: `api/discussions/${id}/members`,
        method: "POST",
        body: { user_ids },
      }),
      invalidatesTags: (_result, _error, { id }) => [LIST, membersTag(id)],
    }),
    removeDiscussionMember: build.mutation<
      unknown,
      { id: number; userId: number }
    >({
      query: ({ id, userId }) => ({
        url: `api/discussions/${id}/members/${userId}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { id }) => [LIST, membersTag(id)],
    }),
    updateDiscussionMembership: build.mutation<
      unknown,
      { id: number; muted?: boolean; read?: boolean }
    >({
      query: ({ id, ...body }) => ({
        url: `api/discussions/${id}/membership`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: [LIST],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_DISCUSSIONS", (payload) => [
  LIST,
  messagesTag(payload.discussion_id),
  membersTag(payload.discussion_id),
]);

export const {
  useGetDiscussionsQuery,
  useGetDiscussionMessagesInfiniteQuery,
  useGetDiscussionMembersQuery,
  useGetCommentThreadsQuery,
  useStartDiscussionMutation,
  useRenameDiscussionMutation,
  useDeleteDiscussionMutation,
  useSendDiscussionMessageMutation,
  useEditDiscussionMessageMutation,
  useDeleteDiscussionMessageMutation,
  useAddDiscussionMembersMutation,
  useRemoveDiscussionMemberMutation,
  useUpdateDiscussionMembershipMutation,
} = discussionsApi;
