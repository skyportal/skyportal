/**
 * The user's conversations with the assistant.
 *
 * Answers are written back out of band by the assistant service, which pushes
 * REFRESH_ASSISTANT to the asking user once it has one.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface AssistantMessage {
  id: number;
  text: string;
  system: boolean;
  channel: string | null;
  created_at: string;
}

export interface AssistantQuestion {
  text: string;
  channel?: string | null | undefined;
  context_type?: string | undefined;
  context_id?: string | undefined;
}

const messagesUrl = (channel: string | null) =>
  channel
    ? `api/assistant/messages?channel=${encodeURIComponent(channel)}`
    : "api/assistant/messages";

export const assistantApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAssistantConversations: build.query<string[], void>({
      query: () => "api/assistant/conversations",
      providesTags: ["Assistant"],
    }),
    getAssistantConversation: build.query<AssistantMessage[], string | null>({
      query: (channel) => messagesUrl(channel),
      providesTags: ["Assistant"],
    }),
    askAssistant: build.mutation<{ id: number }, AssistantQuestion>({
      query: (body) => ({
        url: "api/assistant/messages",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Assistant"],
    }),
    renameAssistantConversation: build.mutation<
      unknown,
      { channel: string; name: string }
    >({
      query: ({ channel, name }) => ({
        url: `api/assistant/conversations?channel=${encodeURIComponent(channel)}`,
        method: "PATCH",
        body: { name },
      }),
      invalidatesTags: ["Assistant"],
    }),
    deleteAssistantConversation: build.mutation<unknown, string>({
      query: (channel) => ({
        url: `api/assistant/conversations?channel=${encodeURIComponent(channel)}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Assistant"],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_ASSISTANT", () => ["Assistant"]);

export const {
  useGetAssistantConversationsQuery,
  useGetAssistantConversationQuery,
  useAskAssistantMutation,
  useRenameAssistantConversationMutation,
  useDeleteAssistantConversationMutation,
} = assistantApi;
