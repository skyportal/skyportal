/**
 * Single instrument (detail view, logs, skymap, mutations).
 *
 * RTK Query conversion of the old `FETCH_INSTRUMENT` duck. The detail query is
 * keyed by instrument id; the logs and skymap reads are triggered imperatively
 * (form submit / effect), so they are exposed as lazy queries. Create / modify
 * / delete / status-update are mutations that invalidate the `Instrument` tag.
 *
 * The websocket `REFRESH_INSTRUMENT` message is bridged to cache invalidation
 * via `invalidateOnMessage`, preserving the old gate: only refresh when the
 * pushed `instrument_id` matches a currently-loaded instrument.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

type Instrument = Record<string, any>;

interface FetchInstrumentLogsArg {
  id: number | string;
  params?: Record<string, unknown> | undefined;
}

interface FetchInstrumentSkymapArg {
  id: number | string;
  localization: { dateobs: string; localization_name: string };
  airmassTime?: string | null | undefined;
}

interface ModifyInstrumentArg {
  id: number | string;
  params: Record<string, unknown>;
}

export const instrumentApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInstrument: build.query<
      RouteData<"GET /api/instrument/{instrument_id}"> & {
        log_exists?: boolean;
      },
      number | string
    >({
      query: (id) => `api/instrument/${id}`,
      providesTags: ["Instrument"],
    }),
    getInstrumentLogs: build.query<Instrument, FetchInstrumentLogsArg>({
      query: ({ id, params = {} }) => ({
        url: `api/instrument/${id}/log`,
        params,
      }),
      providesTags: ["Instrument"],
    }),
    getInstrumentSkymap: build.query<
      RouteData<"GET /api/instrument/{instrument_id}">,
      FetchInstrumentSkymapArg
    >({
      query: ({ id, localization, airmassTime = null }) => {
        const base = `api/instrument/${id}?includeGeoJSONSummary=True&localizationDateobs=${localization.dateobs}&localizationName=${localization.localization_name}`;
        return airmassTime ? `${base}&airmassTime=${airmassTime}` : base;
      },
      providesTags: ["Instrument"],
    }),
    submitInstrument: build.mutation<Instrument, Record<string, unknown>>({
      query: (run) => ({
        url: "api/instrument",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["Instrument"],
    }),
    modifyInstrument: build.mutation<
      RouteData<"PUT /api/instrument/{instrument_id}">,
      ModifyInstrumentArg
    >({
      query: ({ id, params }) => ({
        url: `api/instrument/${id}`,
        method: "PUT",
        body: params,
      }),
      invalidatesTags: ["Instrument"],
    }),
    deleteInstrument: build.mutation<
      RouteData<"DELETE /api/instrument/{instrument_id}">,
      number | string
    >({
      query: (id) => ({
        url: `api/instrument/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Instrument"],
    }),
    updateInstrumentStatus: build.mutation<Instrument, number | string>({
      query: (id) => ({
        url: `api/instrument/${id}/status`,
        method: "PUT",
      }),
      invalidatesTags: ["Instrument"],
    }),
  }),
});

// Websocket: old handler refetched the loaded instrument on REFRESH_INSTRUMENT.
// Invalidating the tag refetches whatever `getInstrument` query is active.
invalidateOnMessage("skyportal/REFRESH_INSTRUMENT", () => ["Instrument"]);

export const {
  useGetInstrumentQuery,
  useLazyGetInstrumentLogsQuery,
  useLazyGetInstrumentSkymapQuery,
  useSubmitInstrumentMutation,
  useModifyInstrumentMutation,
  useDeleteInstrumentMutation,
  useUpdateInstrumentStatusMutation,
} = instrumentApi;
