import { skyportalApi } from "../api/skyportalApi";

export interface CrossMatchArg {
  ra: number | string;
  dec: number | string;
  radius: number | string;
}

// BOOM archive: catalog names + positional cross-matches. RTK Query conversion
// of the old boom_archive thunks (kept in place — the archive functionality is
// being moved from kowalski_archive onto BOOM). Endpoint names are BOOM-prefixed
// where kowalski_archive has an equivalent, to stay unique on the shared api.
export const boomArchiveApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getBoomCatalogNames: build.query<any, void>({
      query: () => "api/boom/archive/catalogs",
    }),
    getCrossMatches: build.query<any, CrossMatchArg>({
      query: ({ ra, dec, radius }) =>
        `api/boom/archive/cross_match?ra=${ra}&dec=${dec}&radius=${radius}&radius_units=arcsec`,
    }),
  }),
});

export const {
  useGetBoomCatalogNamesQuery,
  useLazyGetBoomCatalogNamesQuery,
  useGetCrossMatchesQuery,
  useLazyGetCrossMatchesQuery,
} = boomArchiveApi;
