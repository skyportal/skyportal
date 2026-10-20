/**
 * A single stream (by id).
 *
 * RTK Query conversion of the old `FETCH_STREAM` duck.
 */
import { skyportalApi } from "../api/skyportalApi";
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

export const { useGetStreamQuery } = streamApi;
