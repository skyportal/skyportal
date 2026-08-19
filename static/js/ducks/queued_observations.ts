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

import type {
  ObservationQueues,
  ObservationsPage,
} from "skyportal-js/Observations";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

dayjs.extend(relativeTime);
dayjs.extend(utc);

type FilterParams = Record<string, unknown>;

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
  data?:
    | { queuesOnly?: boolean; startDate?: string; endDate?: string }
    | undefined;
}

interface DeleteAPIQueueArg {
  id: number | string;
  data?: Record<string, unknown> | undefined;
}

export const queuedObservationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getQueuedObservations: build.query<ObservationsPage, FilterParams | void>({
      queryFn: (filterParams, api) => {
        const { startDate, endDate, ...rest } = withQueuedObservationDefaults(
          filterParams ?? {},
        );
        return clientQuery(api, (client) =>
          client.fetchObservations(
            String(startDate ?? ""),
            String(endDate ?? ""),
            rest,
          ),
        );
      },
      providesTags: ["QueuedObservations", "Observation"],
    }),
    getGcnEventQueuedObservations: build.query<
      ObservationsPage,
      FetchGcnEventQueuedObservationsArg
    >({
      queryFn: ({ dateobs, filterParams }, api) => {
        const { startDate, endDate, ...rest } =
          withGcnEventQueuedObservationDefaults(dateobs, filterParams ?? {});
        return clientQuery(api, (client) =>
          client.fetchObservations(
            String(startDate ?? ""),
            String(endDate ?? ""),
            rest,
          ),
        );
      },
      providesTags: ["QueuedObservations", "Observation"],
    }),
    requestAPIQueues: build.query<ObservationQueues, RequestAPIQueuesArg>({
      queryFn: ({ id, data = { queuesOnly: true } }, api) =>
        clientQuery(api, (client) =>
          client.fetchObservationExternalApi(Number(id), data),
        ),
    }),
    deleteAPIQueue: build.mutation<void, DeleteAPIQueueArg>({
      queryFn: ({ id, data }, api) =>
        clientQuery(api, (client) =>
          client.deleteObservationExternalApi(
            Number(id),
            String(data?.["queueName"] ?? ""),
          ),
        ),
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
