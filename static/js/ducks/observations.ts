/**
 * Observations.
 *
 * RTK Query conversion of the old `FETCH_OBSERVATIONS` /
 * `FETCH_GCNEVENT_OBSERVATIONS` duck. The executed-observations list and the
 * GCN-event observations list are queries; submit/upload/treasuremap/external
 * API calls are mutations.
 *
 * The date-window defaulting that the old thunks applied is preserved inside
 * the query builders so callers can pass a sparse filterParams object.
 *
 * Websocket-driven invalidation bridges the old `messageHandler.add(...)`
 * callbacks: `REFRESH_OBSERVATIONS` refetches the observations list, and
 * `FETCH_GCNEVENT_OBSERVATIONS` refetches the GCN-event observations (the old
 * handler gated this on the currently-loaded gcnEvent matching the pushed
 * event id; that condition is preserved).
 */
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

// Extras returned alongside the wrapper that RouteData does not encode.
type ObservationListResponse = RouteData<"GET /api/observation"> & {
  geojson?: object[] | null;
  field_ids?: number[] | null;
  probability?: number | null;
  area?: number | null;
  min_observations_per_field?: number | null;
};

dayjs.extend(relativeTime);
dayjs.extend(utc);

type FilterParams = Record<string, unknown>;

const buildQueryString = (filterParams: FilterParams): string => {
  const params = new URLSearchParams(
    Object.fromEntries(
      Object.entries(filterParams)
        // Drop empty values: String(undefined) would send "instrumentName=undefined",
        // which the backend tries to resolve as an instrument and 500s.
        .filter(([, v]) => v !== undefined && v !== null && v !== "")
        .map(([key, value]) => [key, String(value)]),
    ),
  ).toString();
  return params ? `api/observation?${params}` : "api/observation";
};

const withObservationDefaults = (filterParams: FilterParams): FilterParams => {
  const params = { ...filterParams };
  if (!Object.keys(params).includes("startDate")) {
    params["startDate"] = dayjs()
      .utc()
      .subtract(3650, "day")
      .utc()
      .format("YYYY-MM-DDTHH:mm:ssZ");
  }
  if (!Object.keys(params).includes("endDate")) {
    params["endDate"] = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  }
  if (!Object.keys(params).includes("numPerPage")) {
    params["numPerPage"] = 10;
  }
  return params;
};

const withGcnEventObservationDefaults = (
  dateobs: string,
  filterParams: FilterParams,
): FilterParams => {
  const params = { ...filterParams };
  params["localizationDateobs"] = dateobs;
  params["numPerPage"] = 1000;

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
  return params;
};

interface FetchGcnEventObservationsArg {
  dateobs: string;
  filterParams?: FilterParams | undefined;
}

interface TreasureMapArg {
  id: number | string;
  data: Record<string, unknown>;
}

interface RequestAPIQueuedObservationsArg {
  id: number | string;
  data?: Record<string, unknown> | undefined;
}

export const observationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getObservations: build.query<ObservationListResponse, FilterParams | void>({
      query: (filterParams) =>
        buildQueryString(withObservationDefaults(filterParams ?? {})),
      providesTags: ["Observation"],
    }),
    getGcnEventObservations: build.query<
      ObservationListResponse,
      FetchGcnEventObservationsArg
    >({
      query: ({ dateobs, filterParams }) =>
        buildQueryString(
          withGcnEventObservationDefaults(dateobs, filterParams ?? {}),
        ),
      providesTags: ["GcnEventObservation"],
    }),
    submitObservations: build.mutation<any, Record<string, unknown>>({
      query: (params) => ({
        url: "api/observation",
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["Observation"],
    }),
    uploadObservations: build.mutation<
      RouteData<"POST /api/observation/ascii">,
      Record<string, unknown>
    >({
      query: (data) => ({
        url: "api/observation/ascii",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Observation"],
    }),
    requestAPIObservations: build.mutation<
      RouteData<"POST /api/observation/external_api">,
      Record<string, unknown>
    >({
      query: (data) => ({
        url: "api/observation/external_api",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Observation"],
    }),
    requestAPIQueuedObservations: build.query<
      RouteData<"GET /api/observation/external_api/{allocation_id}">,
      RequestAPIQueuedObservationsArg
    >({
      query: ({ id, data }) => {
        const params = new URLSearchParams(
          Object.fromEntries(
            Object.entries(data ?? {}).map(([key, value]) => [
              key,
              String(value),
            ]),
          ),
        ).toString();
        return params
          ? `api/observation/external_api/${id}?${params}`
          : `api/observation/external_api/${id}`;
      },
    }),
    submitObservationsTreasureMap: build.mutation<any, TreasureMapArg>({
      query: ({ id, data }) => ({
        url: `api/observation/treasuremap/${id}`,
        method: "POST",
        body: data,
      }),
    }),
    deleteObservationsTreasureMap: build.mutation<any, TreasureMapArg>({
      query: ({ id, data }) => ({
        url: `api/observation/treasuremap/${id}`,
        method: "DELETE",
        body: data,
      }),
    }),
  }),
});

// Websocket: the old handler refetched the observations list on
// REFRESH_OBSERVATIONS.
invalidateOnMessage("skyportal/REFRESH_OBSERVATIONS", () => ["Observation"]);

// Websocket: the old handler refetched the GCN-event observations on
// FETCH_GCNEVENT_OBSERVATIONS, but only when the currently-loaded gcnEvent
// matched the pushed event id.
invalidateOnMessage(
  "skyportal/FETCH_GCNEVENT_OBSERVATIONS",
  (payload, getState) => {
    const { gcnEvent } = getState() as {
      gcnEvent?: { id?: number | string } | null;
    };
    if (gcnEvent && gcnEvent.id === payload?.gcnEvent?.id) {
      return ["GcnEventObservation"];
    }
    return null;
  },
);

export const {
  useGetObservationsQuery,
  useLazyGetObservationsQuery,
  useGetGcnEventObservationsQuery,
  useLazyGetGcnEventObservationsQuery,
  useSubmitObservationsMutation,
  useUploadObservationsMutation,
  useRequestAPIObservationsMutation,
  useRequestAPIQueuedObservationsQuery,
  useLazyRequestAPIQueuedObservationsQuery,
  useSubmitObservationsTreasureMapMutation,
  useDeleteObservationsTreasureMapMutation,
} = observationsApi;
