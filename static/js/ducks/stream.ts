/**
 * A single stream (by id).
 *
 * RTK Query conversion of the old `FETCH_STREAM` duck. The old websocket handler
 * only refetched when the currently-loaded stream matched the pushed
 * `stream_id`; here we invalidate the "Stream" tag, which only refetches the
 * active stream query.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export const streamApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getStream: build.query<
      RouteData<"GET /api/streams/{stream_id}">,
      number | string
    >({
      query: (id) => `api/streams/${id}`,
      providesTags: ["Stream"],
    }),
  }),
});

// Websocket: only the active stream query (the one the user has open) is
// invalidated, mirroring the old "loaded_stream_id === payload.stream_id" gate.
invalidateOnMessage("skyportal/REFRESH_STREAM", () => ["Stream"]);

export const { useGetStreamQuery } = streamApi;
