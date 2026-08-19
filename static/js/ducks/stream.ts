/**
 * A single stream (by id).
 *
 * RTK Query conversion of the old `FETCH_STREAM` duck, calling the typed
 * `skyportal-js` client. The old websocket handler only refetched when the
 * currently-loaded stream matched the pushed `stream_id`; here we invalidate the
 * "Stream" tag, which only refetches the active stream query.
 */
import type { Stream } from "skyportal-js/Streams";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const streamApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getStream: build.query<Stream, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchStream(Number(id))),
      providesTags: ["Stream"],
    }),
  }),
});

// Websocket: only the active stream query (the one the user has open) is
// invalidated, mirroring the old "loaded_stream_id === payload.stream_id" gate.
invalidateOnMessage("skyportal/REFRESH_STREAM", () => ["Stream"]);

export const { useGetStreamQuery } = streamApi;
