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
import { clientQuery } from "../api/skyportalClient";

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

export interface OverlayPhotometryDatum {
  filter: string;
  mjd: number;
  mag: number | null;
  mag_corr: number | null;
  extinction: number | null;
}

export const photometryMinimalApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSourcePhotometryMinimal: build.query<
      MinimalPhotometryDatum[],
      number | string
    >({
      // Keep only the fields the old reducer exposed, normalising `origin`.
      queryFn: (id, api) =>
        clientQuery(api, async (client) =>
          (
            await client.fetchPhotometry(String(id), {
              format: "plot",
              magsys: "ab",
              individualOrSeries: "both",
              includeSuperObjsPhotometry: true,
            })
          ).map((datum) => ({
            id: datum.id,
            obj_id: datum.obj_id ?? "",
            filter: datum.filter ?? "",
            limiting_mag: datum.limiting_mag ?? 0,
            mag: datum.mag ?? null,
            magerr: datum.magerr ?? null,
            mjd: datum.mjd ?? 0,
            origin: ["None", ""].includes(datum.origin ?? "")
              ? null
              : (datum.origin ?? null),
          })),
        ),
      providesTags: ["Photometry"],
    }),
    // Photometry for the Source Statistics overlays. When `includeExtinction`
    // is set, the backend adds `mag_corr` (Galactic-extinction-corrected mag,
    // computed per-filter via the G23 law) and `extinction` (A_band).
    getSourcePhotometryOverlay: build.query<
      OverlayPhotometryDatum[],
      { id: number | string; includeExtinction: boolean }
    >({
      queryFn: ({ id, includeExtinction }, api) =>
        clientQuery(api, async (client) =>
          (
            await client.fetchPhotometry(String(id), {
              // format "mag" (not "plot") so the backend attaches `mag_corr`/
              // `extinction` when requested.
              format: "mag",
              magsys: "ab",
              individualOrSeries: "both",
              includeSuperObjsPhotometry: true,
              includeExtinction,
            })
          ).map((datum) => ({
            filter: datum.filter ?? "",
            mjd: datum.mjd ?? 0,
            mag: datum.mag ?? null,
            mag_corr: datum.mag_corr ?? null,
            extinction: datum.extinction ?? null,
          })),
        ),
      providesTags: ["Photometry"],
    }),
  }),
});

export const {
  useGetSourcePhotometryMinimalQuery,
  useGetSourcePhotometryOverlayQuery,
} = photometryMinimalApi;
