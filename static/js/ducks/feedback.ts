import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { components } from "../types/api";

export type Feedback = components["schemas"]["FeedbackResponse"];
export type FeedbackCategory = Feedback["category"];

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
    updateFeedback: build.mutation<unknown, { id: number; resolved: boolean }>({
      query: ({ id, ...body }) => ({
        url: `api/feedback/${id}`,
        method: "PATCH",
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
} = feedbackApi;
