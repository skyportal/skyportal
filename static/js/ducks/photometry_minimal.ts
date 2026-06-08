/**
 * Minimal source photometry (the "photometry_minimal" slice).
 *
 * RTK Query conversion of the old `FETCH_SOURCE_PHOTOMETRY_MINIMAL` duck. The
 * endpoint is injected into the central `skyportalApi`. The backend returns the
 * full photometry payload; the query keeps the old slice shape by mapping each
 * datum to the minimal set of fields consumers expect (id, obj_id, filter,
 * limiting_mag, mag, magerr, mjd, origin).
 *
 * The old duck keyed photometry by source id in a single reducer slice and
 * exposed `clearPhotometryMinimal` to drop cached entries. With RTK Query each
 * source's photometry is its own cache entry (keyed by the `sourceId` query
 * arg), so per-source caching is automatic. There is no websocket refresh for
 * this duck.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface MinimalPhotometryDatum {
  id: number;
  obj_id: string;
  filter: string;
  limiting_mag: number;
  mag: number | null;
  magerr: number | null;
  mjd: number;
  origin: string | null;
}

interface RawPhotometryDatum {
  id: number;
  obj_id: string;
  filter: string;
  limiting_mag: number;
  mag: number | null;
  magerr: number | null;
  mjd: number;
  origin?: string | null;
  [key: string]: unknown;
}

export const photometryMinimalApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSourcePhotometryMinimal: build.query<
      MinimalPhotometryDatum[],
      number | string
    >({
      query: (id) => ({
        url: `api/sources/${id}/photometry`,
        params: {
          format: "plot",
          magsys: "ab",
          individualOrSeries: "both",
          includeSuperObjsPhotometry: true,
        },
      }),
      // Keep only the fields the old reducer exposed, normalising `origin`.
      transformResponse: (data: RawPhotometryDatum[]) =>
        (data ?? []).map((datum) => ({
          id: datum.id,
          obj_id: datum.obj_id,
          filter: datum.filter,
          limiting_mag: datum.limiting_mag,
          mag: datum.mag,
          magerr: datum.magerr,
          mjd: datum.mjd,
          origin: ["None", ""].includes(datum.origin ?? "")
            ? null
            : (datum.origin ?? null),
        })),
      providesTags: ["Photometry"],
    }),
  }),
});

export const { useGetSourcePhotometryMinimalQuery } = photometryMinimalApi;
