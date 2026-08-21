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

import type {
  FetchObservationsOptions,
  ObservationPost,
  ObservationQueues,
  ObservationsPage,
} from "skyportal-js/Observations";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

type ObservationListResponse = ObservationsPage;

dayjs.extend(relativeTime);
dayjs.extend(utc);

type FilterParams = FetchObservationsOptions & {
  startDate?: string;
  endDate?: string;
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
  data: {
    startDate?: string;
    endDate?: string;
    localizationDateobs: string;
    localizationName?: string;
    localizationCumprob?: number;
    numberObservations?: number;
  };
}

interface RequestAPIQueuedObservationsArg {
  id: number | string;
  data?:
    | { queuesOnly?: boolean; startDate?: string; endDate?: string }
    | undefined;
}

export const observationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getObservations: build.query<ObservationListResponse, FilterParams | void>({
      queryFn: (filterParams, api) => {
        const { startDate, endDate, ...rest } = withObservationDefaults(
          filterParams ?? {},
        );
        return clientQuery(api, (client) =>
          client.fetchObservations(startDate ?? "", endDate ?? "", rest),
        );
      },
      providesTags: ["Observation"],
    }),
    getGcnEventObservations: build.query<
      ObservationListResponse,
      FetchGcnEventObservationsArg
    >({
      queryFn: ({ dateobs, filterParams }, api) => {
        const { startDate, endDate, ...rest } = withGcnEventObservationDefaults(
          dateobs,
          filterParams ?? {},
        );
        return clientQuery(api, (client) =>
          client.fetchObservations(startDate ?? "", endDate ?? "", rest),
        );
      },
      providesTags: ["GcnEventObservation"],
    }),
    submitObservations: build.mutation<void, ObservationPost>({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.postObservation(params)),
      invalidatesTags: ["Observation"],
    }),
    uploadObservations: build.mutation<
      void,
      { instrumentID: number | string; observationData: string }
    >({
      queryFn: ({ instrumentID, observationData }, api) =>
        clientQuery(api, (client) =>
          client.postObservationAscii(Number(instrumentID), observationData),
        ),
      invalidatesTags: ["Observation"],
    }),
    requestAPIObservations: build.mutation<
      void,
      { allocation_id: number | string; start_date?: string; end_date?: string }
    >({
      queryFn: ({ allocation_id, start_date, end_date }, api) =>
        clientQuery(api, (client) =>
          client.postObservationExternalApi(Number(allocation_id), {
            startDate: start_date,
            endDate: end_date,
          }),
        ),
      invalidatesTags: ["Observation"],
    }),
    requestAPIQueuedObservations: build.query<
      ObservationQueues,
      RequestAPIQueuedObservationsArg
    >({
      queryFn: ({ id, data }, api) =>
        clientQuery(api, (client) =>
          client.fetchObservationExternalApi(Number(id), data ?? {}),
        ),
    }),
    submitObservationsTreasureMap: build.mutation<void, TreasureMapArg>({
      queryFn: ({ id, data }, api) =>
        clientQuery(api, (client) =>
          client.postObservationTreasuremap(
            Number(id),
            data.startDate ?? "",
            data.endDate ?? "",
            data.localizationDateobs,
            {
              localizationName: data.localizationName,
              localizationCumprob: data.localizationCumprob,
              numberObservations: data.numberObservations,
            },
          ),
        ),
    }),
    deleteObservationsTreasureMap: build.mutation<void, TreasureMapArg>({
      queryFn: ({ id, data }, api) =>
        clientQuery(api, (client) =>
          client.deleteObservationTreasuremap(
            Number(id),
            data.localizationDateobs,
          ),
        ),
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
