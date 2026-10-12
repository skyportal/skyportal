/**
 * Galaxy catalogs.
 *
 * RTK Query conversion of the old `FETCH_GALAXIES` duck. Queries fetch the
 * galaxy list, the per-GCN-event galaxy list, and the list of catalog names;
 * mutations upload a catalog (ascii) and delete a catalog. All share the
 * `Galaxies` tag so a mutation refetches the active galaxy queries.
 */
import { buildQueryString, pickParams } from "../API";
import { skyportalApi } from "../api/skyportalApi";

const QUERY_KEYS = [
  "catalog_name",
  "catalogNamesOnly",
  "galaxyName",
  "ra",
  "dec",
  "radius",
  "minDistance",
  "maxDistance",
  "minRedshift",
  "maxRedshift",
  "minMstar",
  "maxMstar",
  "localizationDateobs",
  "localizationName",
  "localizationCumprob",
  "includeGeoJSON",
  "returnProbability",
  "numPerPage",
  "pageNumber",
  "sortBy",
  "sortOrder",
] as const;

interface GcnEventGalaxiesArg {
  dateobs: string;
  filterParams?: Record<string, unknown> | undefined;
}

interface UploadGalaxiesArg {
  catalogData: string;
  catalogName: string;
  [key: string]: unknown;
}

export const galaxiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGalaxies: build.query<any, Record<string, unknown> | void>({
      query: (filterParams) => {
        const qs = buildQueryString(
          (filterParams as Record<string, unknown>) ?? {},
        );
        return qs ? `api/galaxy_catalog?${qs}` : "api/galaxy_catalog";
      },
      providesTags: ["Galaxies"],
    }),
    getGcnEventGalaxies: build.query<any, GcnEventGalaxiesArg>({
      query: ({ dateobs, filterParams }) => {
        const qs = buildQueryString({
          ...pickParams(filterParams ?? {}, QUERY_KEYS),
          localizationDateobs: dateobs,
          includeGeoJSON: true,
        });
        return `api/galaxy_catalog?${qs}`;
      },
      providesTags: ["Galaxies"],
    }),
    getGalaxyCatalogs: build.query<any, Record<string, unknown> | void>({
      query: (filterParams) => {
        const qs = buildQueryString({
          ...((filterParams as Record<string, unknown>) ?? {}),
          catalogNamesOnly: true,
        });
        return `api/galaxy_catalog?${qs}`;
      },
      providesTags: ["Galaxies"],
    }),
    uploadGalaxies: build.mutation<any, UploadGalaxiesArg>({
      query: (data) => ({
        url: "api/galaxy_catalog/ascii",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Galaxies"],
    }),
    deleteCatalog: build.mutation<any, string>({
      query: (catalog) => ({
        url: `api/galaxy_catalog/${catalog}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Galaxies"],
    }),
  }),
});

export const {
  useGetGalaxiesQuery,
  useLazyGetGalaxiesQuery,
  useGetGcnEventGalaxiesQuery,
  useLazyGetGcnEventGalaxiesQuery,
  useGetGalaxyCatalogsQuery,
  useLazyGetGalaxyCatalogsQuery,
  useUploadGalaxiesMutation,
  useDeleteCatalogMutation,
} = galaxiesApi;
