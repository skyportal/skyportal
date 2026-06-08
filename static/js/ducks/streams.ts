/**
 * Streams.
 *
 * RTK Query conversion of the old `FETCH_STREAMS` duck. The list query provides
 * the "Streams" tag; all mutations (add/delete stream, add/remove a stream from
 * a group, add/remove a user on a stream) invalidate it so the list refetches.
 *
 * The old websocket handler refetched streams on a FETCH_STREAMS message; here
 * we invalidate the "Streams" tag so the active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface Stream {
  id: number;
  name: string;
  [key: string]: unknown;
}

export const streamsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getStreams: build.query<Stream[], void>({
      query: () => "api/streams",
      providesTags: ["Streams"],
    }),
    addNewStream: build.mutation<unknown, Record<string, unknown>>({
      query: (form_data) => ({
        url: "api/streams",
        method: "POST",
        body: form_data,
      }),
      invalidatesTags: ["Streams"],
    }),
    deleteStream: build.mutation<unknown, number | string>({
      query: (stream_id) => ({
        url: `api/streams/${stream_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Streams"],
    }),
    addGroupStream: build.mutation<
      unknown,
      { group_id: number | string; stream_id: number | string }
    >({
      query: ({ group_id, stream_id }) => ({
        url: `api/groups/${group_id}/streams`,
        method: "POST",
        body: { stream_id },
      }),
      invalidatesTags: ["Streams"],
    }),
    deleteGroupStream: build.mutation<
      unknown,
      { group_id: number | string; stream_id: number | string }
    >({
      query: ({ group_id, stream_id }) => ({
        url: `api/groups/${group_id}/streams/${stream_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Streams"],
    }),
    addStreamUser: build.mutation<
      unknown,
      { user_id: number | string; stream_id: number | string }
    >({
      query: ({ user_id, stream_id }) => ({
        url: `api/streams/${stream_id}/users`,
        method: "POST",
        body: { user_id },
      }),
      invalidatesTags: ["Streams"],
    }),
    deleteStreamUser: build.mutation<
      unknown,
      { user_id: number | string; stream_id: number | string }
    >({
      query: ({ user_id, stream_id }) => ({
        url: `api/streams/${stream_id}/users/${user_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Streams"],
    }),
  }),
});

// Websocket: old handler refetched streams on FETCH_STREAMS.
invalidateOnMessage("skyportal/FETCH_STREAMS", () => ["Streams"]);

export const {
  useGetStreamsQuery,
  useAddNewStreamMutation,
  useDeleteStreamMutation,
  useAddGroupStreamMutation,
  useDeleteGroupStreamMutation,
  useAddStreamUserMutation,
  useDeleteStreamUserMutation,
} = streamsApi;
