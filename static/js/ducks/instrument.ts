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
import type {
  FetchInstrumentLogsOptions,
  Instrument,
  InstrumentLog,
  InstrumentPost,
  InstrumentPut,
} from "skyportal-js/Instruments";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface FetchInstrumentLogsArg {
  id: number | string;
  params?: FetchInstrumentLogsOptions | undefined;
}

interface FetchInstrumentSkymapArg {
  id: number | string;
  localization: { dateobs: string; localization_name: string };
  airmassTime?: string | null | undefined;
}

interface ModifyInstrumentArg {
  id: number | string;
  params: InstrumentPut;
}

export const instrumentApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInstrument: build.query<Instrument, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchInstrument(Number(id))),
      providesTags: ["Instrument"],
    }),
    getInstrumentLogs: build.query<InstrumentLog[], FetchInstrumentLogsArg>({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.fetchInstrumentLogs(Number(id), params ?? {}),
        ),
      providesTags: ["Instrument"],
    }),
    getInstrumentSkymap: build.query<Instrument, FetchInstrumentSkymapArg>({
      queryFn: ({ id, localization, airmassTime = null }, api) =>
        clientQuery(api, (client) =>
          client.fetchInstrument(Number(id), {
            includeGeoJSONSummary: true,
            localizationDateobs: localization.dateobs,
            localizationName: localization.localization_name,
            ...(airmassTime ? { airmassTime } : {}),
          }),
        ),
      providesTags: ["Instrument"],
    }),
    submitInstrument: build.mutation<{ id: number }, InstrumentPost>({
      queryFn: (run, api) =>
        clientQuery(api, (client) => client.postInstrument(run)),
      invalidatesTags: ["Instrument"],
    }),
    modifyInstrument: build.mutation<void, ModifyInstrumentArg>({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.updateInstrument(Number(id), params),
        ),
      invalidatesTags: ["Instrument"],
    }),
    deleteInstrument: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteInstrument(Number(id))),
      invalidatesTags: ["Instrument"],
    }),
    updateInstrumentStatus: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.updateInstrumentStatus(Number(id))),
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
