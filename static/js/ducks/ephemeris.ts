/**
 * Telescope ephemerides.
 *
 * RTK Query conversion of the old `FETCH_EPHEMERIDES` duck. The endpoint is
 * injected into the central `skyportalApi`. The query takes the list of
 * telescope ids to fetch ephemerides for and returns the keyed-by-id object
 * the consumers expect.
 */
import { skyportalApi } from "../api/skyportalApi";

export type Ephemerides = Record<string, unknown>;

export const ephemerisApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getEphemerides: build.query<Ephemerides, number[]>({
      query: (telescopeIds) => ({
        url: "api/internal/ephemeris",
        params: { telescopeIds },
      }),
      providesTags: ["Ephemeris"],
    }),
  }),
});

export const { useGetEphemeridesQuery } = ephemerisApi;
