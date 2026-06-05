/**
 * Galaxy catalogs.
 *
 * RTK Query conversion of the old `FETCH_GALAXIES` duck. Queries fetch the
 * galaxy list, the per-GCN-event galaxy list, and the list of catalog names;
 * mutations upload a catalog (ascii) and delete a catalog. All share the
 * `Galaxies` tag so a mutation refetches the active galaxy queries.
 *
 * The websocket `FETCH_GCNEVENT_GALAXIES` message is bridged to cache
 * invalidation, preserving the old guard that only refetched when the
 * currently-loaded GCN event matched the pushed event.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

const buildQueryString = (params: Record<string, unknown>): string =>
  new URLSearchParams(
    Object.entries(params).reduce<Record<string, string>>((acc, [k, v]) => {
      if (v !== undefined && v !== null) {
        acc[k] = String(v);
      }
      return acc;
    }, {}),
  ).toString();

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
          ...(filterParams ?? {}),
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

// Websocket: the old handler refetched the GCN-event galaxy list only when the
// currently-loaded GCN event matched the pushed event.
invalidateOnMessage(
  "skyportal/FETCH_GCNEVENT_GALAXIES",
  (payload, getState) => {
    const { gcnEvent } = (getState() as { gcnEvent?: { id?: number } }) ?? {};
    if (gcnEvent && gcnEvent.id === payload?.gcnEvent?.id) {
      return ["Galaxies"];
    }
    return null;
  },
);

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
