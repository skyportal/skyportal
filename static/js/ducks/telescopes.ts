/**
 * Telescopes.
 *
 * RTK Query conversion of the old `FETCH_TELESCOPES` duck, calling the typed
 * `skyportal-js` client; submit/delete are mutations that invalidate the
 * `Telescope` tag so the list refetches. The single-telescope fetch is kept as a
 * query keyed on id.
 *
 * The old websocket handlers refreshed the currently-loaded telescope on
 * `REFRESH_TELESCOPE` and the whole list on `REFRESH_TELESCOPES`; both are
 * bridged to invalidation of the `Telescope` tag.
 */
import type {
  Telescope,
  TelescopePost,
  TelescopePut,
} from "skyportal-js/Telescopes";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

// The edit form seeds its state from the full telescope object, so only the
// fields the PUT accepts are forwarded. The client's payload type checks the
// list.
const PUT_FIELDS = [
  "name",
  "nickname",
  "lat",
  "lon",
  "elevation",
  "diameter",
  "skycam_link",
  "weather_link",
  "robotic",
  "fixed_location",
] as const satisfies ReadonlyArray<keyof TelescopePut>;

export const telescopesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTelescopes: build.query<Telescope[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchTelescopes()),
      providesTags: ["Telescope"],
    }),
    getTelescope: build.query<Telescope, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchTelescope(Number(id))),
      providesTags: ["Telescope"],
    }),
    submitTelescope: build.mutation<{ id: number }, TelescopePost>({
      queryFn: (tele, api) =>
        clientQuery(api, (client) => client.postTelescope(tele)),
      invalidatesTags: ["Telescope"],
    }),
    updateTelescope: build.mutation<
      void,
      { id: number | string; data: Record<string, any> }
    >({
      queryFn: ({ id, data }, api) => {
        const payload: TelescopePut = Object.fromEntries(
          PUT_FIELDS.filter((key) => key in data).map((key) => [
            key,
            data[key],
          ]),
        );
        return clientQuery(api, (client) =>
          client.updateTelescope(Number(id), payload),
        );
      },
      invalidatesTags: ["Telescope"],
    }),
    deleteTelescope: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteTelescope(Number(id))),
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
