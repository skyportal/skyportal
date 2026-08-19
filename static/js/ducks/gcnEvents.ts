/**
 * GCN events (the paginated/filterable "gcnEvents" listing).
 *
 * RTK Query conversion of the old `FETCH_GCN_EVENTS` duck. The list query is
 * injected into the central `skyportalApi`, keyed by its filter params (so each
 * distinct page/filter is cached independently) and tagged `GcnEvent`.
 * Add/remove user are mutations that invalidate the `GcnEvent` tag so the list
 * refetches.
 *
 * The websocket `REFRESH_GCN_EVENTS` message is bridged to cache invalidation
 * via `invalidateOnMessage`.
 */
import type {
  FetchGcnEventsOptions,
  GcnEventsPage,
} from "skyportal-js/GcnEvents";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type GcnEventsResult = GcnEventsPage;

export const gcnEventsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGcnEvents: build.query<GcnEventsPage, FetchGcnEventsOptions | void>({
      queryFn: (filterParams, api) =>
        clientQuery(api, (client) => client.fetchGcnEvents(filterParams ?? {})),
      providesTags: ["GcnEvent"],
    }),
    addGcnEventUser: build.mutation<
      void,
      { userID: number | string; gcnEventDateobs: string }
    >({
      queryFn: ({ userID, gcnEventDateobs }, api) =>
        clientQuery(api, (client) =>
          client.postGcnEventUser(gcnEventDateobs, Number(userID)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnEventUser: build.mutation<
      void,
      { userID: number | string; gcnEventDateobs: string }
    >({
      queryFn: ({ userID, gcnEventDateobs }, api) =>
        clientQuery(api, (client) =>
          client.deleteGcnEventUser(gcnEventDateobs, Number(userID)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
  }),
});

// Websocket-driven invalidation: refresh gcn events on REFRESH_GCN_EVENTS.
invalidateOnMessage("skyportal/REFRESH_GCN_EVENTS", () => ["GcnEvent"]);

export const {
  useGetGcnEventsQuery,
  useLazyGetGcnEventsQuery,
  useAddGcnEventUserMutation,
  useDeleteGcnEventUserMutation,
} = gcnEventsApi;
