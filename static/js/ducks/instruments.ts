/**
 * Instruments: the shared instrument list, the per-instrument followup form
 * params, the per-instrument observation-plan form params, and the
 * GCN-event-scoped instrument list.
 *
 * RTK Query conversion of the old `FETCH_INSTRUMENTS` /
 * `FETCH_INSTRUMENT_FORMS` / `FETCH_INSTRUMENT_OBSPLAN_FORMS` /
 * `FETCH_GCNEVENT_INSTRUMENTS` duck. Each is now an injected endpoint.
 *
 * The old websocket handler refetched the instrument list and the followup
 * form params on `REFRESH_INSTRUMENTS`; here we invalidate the matching tags so
 * the active queries refetch.
 */
import type {
  FetchInstrumentsOptions,
  Instrument,
} from "skyportal-js/Instruments";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export type InstrumentFormParams = Record<string, any>;

export const instrumentsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInstruments: build.query<Instrument[], FetchInstrumentsOptions | void>({
      queryFn: (filterParams, api) =>
        clientQuery(api, (client) =>
          client.fetchInstruments(filterParams ?? {}),
        ),
      providesTags: ["Instruments"],
    }),
    getInstrumentForms: build.query<InstrumentFormParams, void>({
      query: () => ({
        url: "api/internal/instrument_forms",
        params: { apiType: "api_classname" },
      }),
      providesTags: ["InstrumentForms"],
    }),
    getInstrumentObsplanForms: build.query<InstrumentFormParams, void>({
      query: () => ({
        url: "api/internal/instrument_forms",
        params: { apiType: "api_classname_obsplan" },
      }),
      providesTags: ["InstrumentObsplanForms"],
    }),
    // raw, and unused: `/api/instrument` without an id only reads `name`, so
    // the localization/GeoJSON params below are dropped by the handler.
    getGcnEventInstruments: build.query<
      RouteData<"GET /api/instrument">,
      { dateobs: string; filterParams?: Record<string, any> | undefined }
    >({
      query: ({ dateobs, filterParams = {} }) => ({
        url: "api/instrument",
        params: {
          ...filterParams,
          localizationDateobs: dateobs,
          includeGeoJSONSummary: true,
          includeGeoJSON: false,
        },
      }),
      providesTags: ["GcnEventInstruments"],
    }),
  }),
});

// Websocket: old handler refetched instruments + followup forms on
// REFRESH_INSTRUMENTS.
invalidateOnMessage("skyportal/REFRESH_INSTRUMENTS", () => [
  "Instruments",
  "InstrumentForms",
]);

export const {
  useGetInstrumentsQuery,
  useLazyGetInstrumentsQuery,
  useGetInstrumentFormsQuery,
  useGetInstrumentObsplanFormsQuery,
  useGetGcnEventInstrumentsQuery,
} = instrumentsApi;
