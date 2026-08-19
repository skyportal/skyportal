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
import type {
  FetchGalaxiesOptions,
  GalaxiesPage,
  GalaxyCatalogAsciiPost,
  GalaxyCatalogCount,
} from "skyportal-js/Galaxies";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface GcnEventGalaxiesArg {
  dateobs: string;
  filterParams?: FetchGalaxiesOptions | undefined;
}

export const galaxiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGalaxies: build.query<GalaxiesPage, FetchGalaxiesOptions | void>({
      queryFn: (filterParams, api) =>
        clientQuery(api, (client) => client.fetchGalaxies(filterParams ?? {})),
      providesTags: ["Galaxies"],
    }),
    getGcnEventGalaxies: build.query<GalaxiesPage, GcnEventGalaxiesArg>({
      queryFn: ({ dateobs, filterParams }, api) =>
        clientQuery(api, (client) =>
          client.fetchGalaxies({
            ...(filterParams ?? {}),
            localizationDateobs: dateobs,
            includeGeoJSON: true,
          }),
        ),
      providesTags: ["Galaxies"],
    }),
    getGalaxyCatalogs: build.query<GalaxyCatalogCount[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchGalaxyCatalogs()),
      providesTags: ["Galaxies"],
    }),
    uploadGalaxies: build.mutation<void, GalaxyCatalogAsciiPost>({
      queryFn: (data, api) =>
        clientQuery(api, (client) => client.postGalaxyCatalogAscii(data)),
      invalidatesTags: ["Galaxies"],
    }),
    deleteCatalog: build.mutation<void, string>({
      queryFn: (catalog, api) =>
        clientQuery(api, (client) => client.deleteGalaxyCatalog(catalog)),
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
