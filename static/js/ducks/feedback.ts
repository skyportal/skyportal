import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { components } from "../types/api";
import { useGetProfileQuery, useHasPermission } from "./profile";

export type Feedback = components["schemas"]["FeedbackResponse"];
export type FeedbackCategory = Feedback["category"];
export type FeedbackStatus = "open" | "answered" | "resolved";

export const statusOf = (message: Feedback): FeedbackStatus => {
  if (message.resolved) return "resolved";
  const replies = message.replies ?? [];
  const last = replies[replies.length - 1];
  return last && last.author.id !== message.author.id ? "answered" : "open";
};

export const feedbackApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFeedback: build.query<Feedback[], void>({
      query: () => "api/feedback",
      transformResponse: (data: { messages: Feedback[] }) => data.messages,
      providesTags: ["Feedback"],
    }),
    addFeedback: build.mutation<
      { id: number },
      { category: FeedbackCategory; text: string }
    >({
      query: (body) => ({ url: "api/feedback", method: "POST", body }),
      invalidatesTags: ["Feedback"],
    }),
    updateFeedback: build.mutation<
      unknown,
      {
        id: number;
        resolved?: boolean;
        assignee_id?: number | null;
        pr_urls?: string[];
      }
    >({
      query: ({ id, ...body }) => ({
        url: `api/feedback/${id}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["Feedback"],
    }),
    replyToFeedback: build.mutation<
      { id: number },
      { id: number; text: string }
    >({
      query: ({ id, ...body }) => ({
        url: `api/feedback/${id}/replies`,
        method: "POST",
        body,
      }),
      invalidatesTags: ["Feedback"],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_FEEDBACK", () => ["Feedback"]);

export const {
  useGetFeedbackQuery,
  useAddFeedbackMutation,
  useUpdateFeedbackMutation,
  useReplyToFeedbackMutation,
} = feedbackApi;

export const useOpenFeedbackCount = () => {
  const isAdmin = useHasPermission("System admin");
  const { data: profile } = useGetProfileQuery();
  const followsFeedback =
    profile?.preferences?.["notifications"]?.feedback?.active === true;
  const { data = [] } = feedbackApi.useGetFeedbackQuery(undefined, {
    skip: !isAdmin || !followsFeedback,
  });
  return data.filter((message) => statusOf(message) === "open").length;
};
