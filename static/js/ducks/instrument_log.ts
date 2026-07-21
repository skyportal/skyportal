/**
 * Instrument log (external follow-up API).
 *
 * RTK Query conversion of the old `FETCH_INSTRUMENT_EXTERNAL_LOG` duck. The
 * request hits the instrument's external follow-up API and is triggered
 * imperatively from a form submit rather than on mount, so it is exposed as a
 * lazy query. The query carries the assigned `InstrumentLog` tag.
 */
import { skyportalApi } from "../api/skyportalApi";

interface FetchInstrumentLogExternalArg {
  id: number | string;
  params?: Record<string, unknown> | undefined;
}

export const instrumentLogApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    fetchInstrumentLogExternal: build.query<
      unknown,
      FetchInstrumentLogExternalArg
    >({
      query: ({ id, params = {} }) => ({
        url: `api/instrument/${id}/external_api`,
        params,
      }),
      providesTags: ["InstrumentLog"],
    }),
  }),
});

export const {
  useFetchInstrumentLogExternalQuery,
  useLazyFetchInstrumentLogExternalQuery,
} = instrumentLogApi;
