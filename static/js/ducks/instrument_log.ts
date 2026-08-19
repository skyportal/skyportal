/**
 * Instrument log (external follow-up API).
 *
 * RTK Query conversion of the old `FETCH_INSTRUMENT_EXTERNAL_LOG` duck, calling
 * the typed `skyportal-js` client. The request hits the instrument's external
 * follow-up API and is triggered imperatively from a form submit rather than on
 * mount, so it is exposed as a lazy query. The query carries the assigned
 * `InstrumentLog` tag.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

interface FetchInstrumentLogExternalArg {
  /** ID of the allocation whose instrument log is requested. */
  id: number | string;
  params: { startDate: string; endDate: string };
}

export const instrumentLogApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    fetchInstrumentLogExternal: build.query<
      void,
      FetchInstrumentLogExternalArg
    >({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.fetchInstrumentLogExternalApi(
            Number(id),
            params.startDate,
            params.endDate,
          ),
        ),
      providesTags: ["InstrumentLog"],
    }),
  }),
});

export const {
  useFetchInstrumentLogExternalQuery,
  useLazyFetchInstrumentLogExternalQuery,
} = instrumentLogApi;
