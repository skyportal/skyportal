/**
 * Streams.
 *
 * RTK Query conversion of the old `FETCH_STREAMS` duck. The list query provides
 * the "Streams" tag; all mutations (add/delete stream, add/remove a stream from
 * a group, add/remove a user on a stream) invalidate it so the list refetches.
 * Endpoints call the typed `skyportal-js` client.
 *
 * The old websocket handler refetched streams on a FETCH_STREAMS message; here
 * we invalidate the "Streams" tag so the active query refetches.
 */
import type {
  Stream,
  StreamPostResponse,
  StreamUserPostResponse,
} from "skyportal-js/Streams";
import type { GroupStreamPostResponse } from "skyportal-js/Groups";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface AddNewStreamArg {
  name: string;
  altdata?: Record<string, unknown>;
  auto_join?: boolean;
}

export const streamsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getStreams: build.query<Stream[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchStreams()),
      providesTags: ["Streams"],
    }),
    addNewStream: build.mutation<StreamPostResponse, AddNewStreamArg>({
      queryFn: ({ name, altdata, auto_join }, api) =>
        clientQuery(api, (client) =>
          client.postStream(name, { altdata, autoJoin: auto_join }),
        ),
      invalidatesTags: ["Streams"],
    }),
    deleteStream: build.mutation<void, number | string>({
      queryFn: (stream_id, api) =>
        clientQuery(api, (client) => client.deleteStream(Number(stream_id))),
      invalidatesTags: ["Streams"],
    }),
    addGroupStream: build.mutation<
      GroupStreamPostResponse,
      { group_id: number | string; stream_id: number | string }
    >({
      queryFn: ({ group_id, stream_id }, api) =>
        clientQuery(api, (client) =>
          client.postGroupStream(Number(group_id), Number(stream_id)),
        ),
      invalidatesTags: ["Streams"],
    }),
    deleteGroupStream: build.mutation<
      void,
      { group_id: number | string; stream_id: number | string }
    >({
      queryFn: ({ group_id, stream_id }, api) =>
        clientQuery(api, (client) =>
          client.deleteGroupStream(Number(group_id), Number(stream_id)),
        ),
      invalidatesTags: ["Streams"],
    }),
    addStreamUser: build.mutation<
      StreamUserPostResponse,
      { user_id: number | string; stream_id: number | string }
    >({
      queryFn: ({ user_id, stream_id }, api) =>
        clientQuery(api, (client) =>
          client.postStreamUser(Number(stream_id), Number(user_id)),
        ),
      // Profile too: a user self-joining an auto-join stream changes their own
      // stream membership, so their profile must refetch.
      invalidatesTags: ["Streams", "Profile"],
    }),
    deleteStreamUser: build.mutation<
      void,
      { user_id: number | string; stream_id: number | string }
    >({
      queryFn: ({ user_id, stream_id }, api) =>
        clientQuery(api, (client) =>
          client.deleteStreamUser(Number(stream_id), Number(user_id)),
        ),
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
