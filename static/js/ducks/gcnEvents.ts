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
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface GcnEventsResult {
  events?: Record<string, any>[] | undefined;
  totalMatches?: number | undefined;
  [key: string]: any;
}

/**
 * Builds a query string from filter params, dropping empty/null/undefined
 * values to mirror the old `API.GET` `filterOutEmptyValues` behaviour.
 */
const buildGcnEventsQuery = (filterParams: Record<string, any>): string => {
  const queryString = buildQueryString(filterParams);
  return `api/gcn_event${queryString ? `?${queryString}` : ""}`;
};

export const gcnEventsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGcnEvents: build.query<GcnEventsResult, Record<string, any> | void>({
      query: (filterParams) => buildGcnEventsQuery(filterParams ?? {}),
      providesTags: ["GcnEvent"],
    }),
    addGcnEventUser: build.mutation<
      unknown,
      { userID: number | string; gcnEventDateobs: string }
    >({
      query: ({ userID, gcnEventDateobs }) => ({
        url: `api/gcn_event/${gcnEventDateobs}/users`,
        method: "POST",
        body: { userID },
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnEventUser: build.mutation<
      unknown,
      { userID: number | string; gcnEventDateobs: string }
    >({
      query: ({ userID, gcnEventDateobs }) => ({
        url: `api/gcn_event/${gcnEventDateobs}/users/${userID}`,
        method: "DELETE",
      }),
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
