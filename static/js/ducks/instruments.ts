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
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type Instrument = Record<string, any>;
export type InstrumentFormParams = Record<string, any>;

export const instrumentsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInstruments: build.query<Instrument[], Record<string, any> | void>({
      query: (filterParams) => ({
        url: "api/instrument",
        params: filterParams || {},
      }),
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
    getGcnEventInstruments: build.query<
      Instrument[],
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
