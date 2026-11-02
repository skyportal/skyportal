import { skyportalApi } from "../api/skyportalApi";
import type { components } from "../types/api";

export type Topic = components["schemas"]["TopicResponse"];
export type TopicFeedItem = components["schemas"]["TopicFeedItemResponse"];
export type TopicFeedPage = components["schemas"]["TopicFeedResponse"];

export interface TopicFields {
  name: string;
  description: string | null;
  classifications: string[];
  tag_ids: number[];
}

const LIST = { type: "Topics" as const, id: "LIST" };
const FEED = { type: "Topics" as const, id: "FEED" };

export const topicsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTopics: build.query<Topic[], void>({
      query: () => "api/topics",
      transformResponse: (data: { topics: Topic[] }) => data.topics,
      providesTags: [LIST],
    }),
    getTopicFeed: build.infiniteQuery<
      TopicFeedPage,
      number | null,
      string | null
    >({
      infiniteQueryOptions: {
        initialPageParam: null,
        getNextPageParam: (lastPage) =>
          lastPage.has_more
            ? lastPage.items?.[lastPage.items.length - 1]?.time
            : undefined,
      },
      query: ({ queryArg, pageParam }) => {
        const params = new URLSearchParams();
        if (queryArg) params.set("topic_id", String(queryArg));
        if (pageParam) params.set("before", pageParam);
        const search = params.toString();
        return `api/topics/feed${search ? `?${search}` : ""}`;
      },
      providesTags: [FEED],
    }),
    createTopic: build.mutation<{ id: number }, TopicFields>({
      query: (body) => ({ url: "api/topics", method: "POST", body }),
      invalidatesTags: [LIST, FEED],
    }),
    updateTopic: build.mutation<unknown, TopicFields & { id: number }>({
      query: ({ id, ...body }) => ({
        url: `api/topics/${id}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: [LIST, FEED],
    }),
    deleteTopic: build.mutation<unknown, number>({
      query: (id) => ({ url: `api/topics/${id}`, method: "DELETE" }),
      invalidatesTags: [LIST, FEED],
    }),
    subscribeToTopic: build.mutation<unknown, number>({
      query: (id) => ({ url: `api/topics/${id}/subscription`, method: "POST" }),
      invalidatesTags: [LIST, FEED],
    }),
    unsubscribeFromTopic: build.mutation<unknown, number>({
      query: (id) => ({
        url: `api/topics/${id}/subscription`,
        method: "DELETE",
      }),
      invalidatesTags: [LIST, FEED],
    }),
    postTopicSource: build.mutation<
      { id: number },
      { id: number; obj_id: string; text: string }
    >({
      query: ({ id, ...body }) => ({
        url: `api/topics/${id}/sources`,
        method: "POST",
        body,
      }),
      invalidatesTags: [FEED],
    }),
    removeTopicSource: build.mutation<unknown, { id: number; objId: string }>({
      query: ({ id, objId }) => ({
        url: `api/topics/${id}/sources/${encodeURIComponent(objId)}`,
        method: "DELETE",
      }),
      invalidatesTags: [FEED],
    }),
  }),
});

export const {
  useGetTopicsQuery,
  useGetTopicFeedInfiniteQuery,
  useCreateTopicMutation,
  useUpdateTopicMutation,
  useDeleteTopicMutation,
  useSubscribeToTopicMutation,
  useUnsubscribeFromTopicMutation,
  usePostTopicSourceMutation,
  useRemoveTopicSourceMutation,
} = topicsApi;
