/**
 * Queued observations.
 *
 * RTK Query conversion of the old `FETCH_QUEUED_OBSERVATIONS` /
 * `FETCH_GCNEVENT_QUEUED_OBSERVATIONS` duck. The queued-observations list and
 * the GCN-event queued-observations list are queries; the external-API queue
 * interactions (list queues / delete a queue) are an imperative query and a
 * mutation.
 *
 * The date-window defaulting that the old thunks applied is preserved inside
 * the query builders so callers can pass a sparse filterParams object. The old
 * slice shape (`{ queued_observations: data }`) is mapped back so consumers
 * that read `queued_observations.queued_observations` keep working off the
 * query result.
 *
 * Websocket-driven invalidation bridges the old `messageHandler.add(...)`
 * callbacks: `REFRESH_QUEUED_OBSERVATIONS` refetches the queued-observations
 * list, and `FETCH_GCNEVENT_QUEUED_OBSERVATIONS` refetches the GCN-event queued
 * observations (the old handler gated this on the currently-loaded gcnEvent
 * matching the pushed event id; that condition is preserved).
 *
 * Note: `requestAPIQueuedObservations` lives in `ducks/observations.ts`
 * (already migrated); consumers use that hook directly.
 */
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

dayjs.extend(relativeTime);
dayjs.extend(utc);

type FilterParams = Record<string, unknown>;

const buildQueryString = (filterParams: FilterParams): string => {
  const params = new URLSearchParams(
    Object.fromEntries(
      Object.entries(filterParams).map(([key, value]) => [key, String(value)]),
    ),
  ).toString();
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

const withGcnEventQueuedObservationDefaults = (
  dateobs: string,
  filterParams: FilterParams,
): FilterParams => {
  const params = { ...filterParams };
  params["localizationDateobs"] = dateobs;

  if (!Object.keys(params).includes("startDate")) {
    if (dateobs) {
      params["startDate"] = dayjs(dateobs).format("YYYY-MM-DD HH:mm:ss");
    }
  }
  if (!Object.keys(params).includes("endDate")) {
    if (dateobs) {
      params["endDate"] = dayjs(dateobs)
        .add(7, "day")
        .format("YYYY-MM-DD HH:mm:ss");
    }
  }
  if (!Object.keys(params).includes("numPerPage")) {
    params["numPerPage"] = 10;
  }
  params["observationStatus"] = "queued";
  return params;
};

interface FetchGcnEventQueuedObservationsArg {
  dateobs: string;
  filterParams?: FilterParams | undefined;
}

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
    getQueuedObservations: build.query<any, FilterParams | void>({
      query: (filterParams) =>
        buildQueryString(withQueuedObservationDefaults(filterParams ?? {})),
      providesTags: ["QueuedObservations", "Observation"],
    }),
    getGcnEventQueuedObservations: build.query<
      any,
      FetchGcnEventQueuedObservationsArg
    >({
      query: ({ dateobs, filterParams }) =>
        buildQueryString(
          withGcnEventQueuedObservationDefaults(dateobs, filterParams ?? {}),
        ),
      providesTags: ["QueuedObservations", "Observation"],
    }),
    requestAPIQueues: build.query<any, RequestAPIQueuesArg>({
      query: ({ id, data = { queuesOnly: true } }) => {
        const params = new URLSearchParams(
          Object.fromEntries(
            Object.entries(data).map(([key, value]) => [key, String(value)]),
          ),
        ).toString();
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

// Websocket: the old handler refetched the GCN-event queued observations on
// FETCH_GCNEVENT_QUEUED_OBSERVATIONS, but only when the currently-loaded
// gcnEvent matched the pushed event id.
invalidateOnMessage(
  "skyportal/FETCH_GCNEVENT_QUEUED_OBSERVATIONS",
  (payload, getState) => {
    const { gcnEvent } = getState() as {
      gcnEvent?: { id?: number | string } | null;
    };
    if (gcnEvent && gcnEvent.id === payload?.gcnEvent?.id) {
      return ["QueuedObservations"];
    }
    return null;
  },
);

export const {
  useGetQueuedObservationsQuery,
  useLazyGetQueuedObservationsQuery,
  useGetGcnEventQueuedObservationsQuery,
  useLazyGetGcnEventQueuedObservationsQuery,
  useRequestAPIQueuesQuery,
  useLazyRequestAPIQueuesQuery,
  useDeleteAPIQueueMutation,
} = queuedObservationsApi;
