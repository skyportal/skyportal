/**
 * Shared assistant queries and their per-user subscriptions.
 *
 * The list is group-scoped server-side (queries tied to a group you belong to);
 * mutations invalidate the `AssistantQueries` tag so it refetches. The websocket
 * `REFRESH_ASSISTANT_QUERIES` message is bridged to invalidation as well.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface AssistantQuery {
  id: number;
  name: string;
  description: string | null;
  prompt: string;
  group_id: number;
  group_name: string | null;
  owner_id: number;
  analysis_service_match: string | null;
  notify_groups: number[] | null;
  context_type: string;
  active: boolean;
  dry_run: boolean;
  subscriber_count: number;
  subscribed: boolean;
  is_owner: boolean;
}

export const assistantQueriesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAssistantQueries: build.query<AssistantQuery[], void>({
      query: () => ({ url: "api/assistant_queries" }),
      providesTags: ["AssistantQueries"],
    }),
    createAssistantQuery: build.mutation<unknown, Record<string, unknown>>({
      query: (body) => ({
        url: "api/assistant_queries",
        method: "POST",
        body,
      }),
      invalidatesTags: ["AssistantQueries"],
    }),
    updateAssistantQuery: build.mutation<
      unknown,
      { id: number; body: Record<string, unknown> }
    >({
      query: ({ id, body }) => ({
        url: `api/assistant_queries/${id}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["AssistantQueries"],
    }),
    deleteAssistantQuery: build.mutation<unknown, number>({
      query: (id) => ({
        url: `api/assistant_queries/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["AssistantQueries"],
    }),
    subscribeAssistantQuery: build.mutation<unknown, number>({
      query: (id) => ({
        url: `api/assistant_queries/${id}/subscription`,
        method: "POST",
      }),
      invalidatesTags: ["AssistantQueries"],
    }),
    unsubscribeAssistantQuery: build.mutation<unknown, number>({
      query: (id) => ({
        url: `api/assistant_queries/${id}/subscription`,
        method: "DELETE",
      }),
      invalidatesTags: ["AssistantQueries"],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_ASSISTANT_QUERIES", () => [
  "AssistantQueries",
]);

export const {
  useGetAssistantQueriesQuery,
  useCreateAssistantQueryMutation,
  useUpdateAssistantQueryMutation,
  useDeleteAssistantQueryMutation,
  useSubscribeAssistantQueryMutation,
  useUnsubscribeAssistantQueryMutation,
} = assistantQueriesApi;
