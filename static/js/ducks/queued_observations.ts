/**
 * Queued observations.
 *
 * RTK Query conversion of the old `FETCH_QUEUED_OBSERVATIONS` duck. The
 * queued-observations list is a query; the external-API queue interactions
 * (list queues / delete a queue) are an imperative query and a mutation.
 *
 * The date-window defaulting that the old thunks applied is preserved inside
 * the query builders so callers can pass a sparse filterParams object. The old
 * slice shape (`{ queued_observations: data }`) is mapped back so consumers
 * that read `queued_observations.queued_observations` keep working off the
 * query result.
 *
 * Websocket-driven invalidation bridges the old `messageHandler.add(...)`
 * callback: `REFRESH_QUEUED_OBSERVATIONS` refetches the queued-observations
 * list.
 *
 * Note: `requestAPIQueuedObservations` lives in `ducks/observations.ts`
 * (already migrated); consumers use that hook directly.
 */
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { buildQueryString as buildQuery } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { components } from "../types/api";
import type { RouteData } from "../types/routeSchemaMap";

dayjs.extend(relativeTime);
dayjs.extend(utc);

type FilterParams = Record<string, unknown>;

const buildQueryString = (filterParams: FilterParams): string => {
  const params = buildQuery(filterParams);
  return params ? `api/observation?${params}` : "api/observation";
};

const withQueuedObservationDefaults = (
  filterParams: FilterParams,
): FilterParams => {
  const params = { ...filterParams };
  if (!Object.keys(params).includes("startDate")) {
    params["startDate"] = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  }
  if (!Object.keys(params).includes("endDate")) {
    params["endDate"] = dayjs()
      .utc()
      .add(7, "day")
      .utc()
      .format("YYYY-MM-DDTHH:mm:ssZ");
  }
  params["observationStatus"] = "queued";
  return params;
};

interface RequestAPIQueuesArg {
  id: number | string;
  data?: Record<string, unknown> | undefined;
}

interface DeleteAPIQueueArg {
  id: number | string;
  data?: Record<string, unknown> | undefined;
}

export const queuedObservationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getQueuedObservations: build.query<
      {
        observations: components["schemas"]["QueuedObservation"][];
        totalMatches: number;
        geojson?: object[] | null;
        field_ids?: number[] | null;
        probability?: number | null;
        area?: number | null;
        min_observations_per_field?: number | null;
      },
      FilterParams | void
    >({
      query: (filterParams) =>
        buildQueryString(withQueuedObservationDefaults(filterParams ?? {})),
      providesTags: ["QueuedObservations", "Observation"],
    }),
    requestAPIQueues: build.query<
      RouteData<"GET /api/observation/external_api/{allocation_id}">,
      RequestAPIQueuesArg
    >({
      query: ({ id, data = { queuesOnly: true } }) => {
        const params = buildQuery(data);
        return params
          ? `api/observation/external_api/${id}?${params}`
          : `api/observation/external_api/${id}`;
      },
    }),
    deleteAPIQueue: build.mutation<any, DeleteAPIQueueArg>({
      query: ({ id, data = {} }) => ({
        url: `api/observation/external_api/${id}`,
        method: "DELETE",
        body: data,
      }),
      invalidatesTags: ["QueuedObservations", "Observation"],
    }),
  }),
});

// Websocket: the old handler refetched the queued-observations list on
// REFRESH_QUEUED_OBSERVATIONS.
invalidateOnMessage("skyportal/REFRESH_QUEUED_OBSERVATIONS", () => [
  "QueuedObservations",
]);

export const {
  useGetQueuedObservationsQuery,
  useLazyGetQueuedObservationsQuery,
  useRequestAPIQueuesQuery,
  useLazyRequestAPIQueuesQuery,
  useDeleteAPIQueueMutation,
} = queuedObservationsApi;
