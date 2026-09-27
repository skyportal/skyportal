import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { buildQueryString as toQueryString, pickParams } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

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

const QUERY_KEYS = [
  "startDate",
  "endDate",
  "localizationDateobs",
  "localizationName",
  "localizationCumprob",
  "instrumentName",
  "telescopeName",
  "numberObservations",
  "observationStatus",
  "returnStatistics",
  "statsLogging",
  "statsMethod",
  "includeGeoJSON",
  "numPerPage",
  "pageNumber",
  "sortBy",
  "sortOrder",
] as const;

const buildQueryString = (filterParams: FilterParams): string => {
  const params = toQueryString(filterParams);
  return params ? `api/observation?${params}` : "api/observation";
};

const withObservationDefaults = (filterParams: FilterParams): FilterParams => {
  const params = pickParams(filterParams, QUERY_KEYS);
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
    params["numPerPage"] = 25;
  }
  return params;
};

const withGcnEventObservationDefaults = (
  dateobs: string,
  filterParams: FilterParams,
): FilterParams => {
  const params = pickParams(filterParams, QUERY_KEYS);
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
        const params = toQueryString(data ?? {});
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

invalidateOnMessage("skyportal/REFRESH_OBSERVATIONS", () => ["Observation"]);

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
