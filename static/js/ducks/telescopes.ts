/**
 * Telescopes.
 *
 * RTK Query conversion of the old `FETCH_TELESCOPES` duck. The list endpoint is
 * injected into the central `skyportalApi`; submit/delete are mutations that
 * invalidate the `Telescope` tag so the list refetches. The single-telescope
 * fetch is kept as a query keyed on id.
 *
 * The old websocket handlers refreshed the currently-loaded telescope on
 * `REFRESH_TELESCOPE` and the whole list on `REFRESH_TELESCOPES`; both are
 * bridged to invalidation of the `Telescope` tag.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type Telescope = Record<string, any>;

export const telescopesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTelescopes: build.query<Telescope[], void>({
      query: () => "api/telescope",
      providesTags: ["Telescope"],
    }),
    getTelescope: build.query<Telescope, number | string>({
      query: (id) => `api/telescope/${id}`,
      providesTags: ["Telescope"],
    }),
    submitTelescope: build.mutation<unknown, Record<string, any>>({
      query: (tele) => ({
        url: "api/telescope",
        method: "POST",
        body: tele,
      }),
      invalidatesTags: ["Telescope"],
    }),
    updateTelescope: build.mutation<
      unknown,
      { id: number | string; data: Record<string, any> }
    >({
      query: ({ id, data }) => ({
        url: `api/telescope/${id}`,
        method: "PUT",
        body: data,
      }),
      invalidatesTags: ["Telescope"],
    }),
    deleteTelescope: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/telescope/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Telescope"],
    }),
  }),
});

// Websocket: old handlers refetched on REFRESH_TELESCOPE / REFRESH_TELESCOPES.
invalidateOnMessage("skyportal/REFRESH_TELESCOPE", () => ["Telescope"]);
invalidateOnMessage("skyportal/REFRESH_TELESCOPES", () => ["Telescope"]);

export const {
  useGetTelescopesQuery,
  useGetTelescopeQuery,
  useSubmitTelescopeMutation,
  useUpdateTelescopeMutation,
  useDeleteTelescopeMutation,
} = telescopesApi;
