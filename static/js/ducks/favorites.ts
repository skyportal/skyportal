/**
 * Favorites (the "favorites" listing).
 *
 * RTK Query conversion of the old `FETCH_FAVORITES` duck. The endpoint is
 * injected into the central `skyportalApi`. The backend returns an array of
 * listing entries; the query keeps the old slice shape by mapping those to the
 * list of `obj_id`s consumers expect. Add/remove are mutations that invalidate
 * the `Favorite` tag so the list refetches.
 *
 * The websocket `REFRESH_FAVORITES` message is bridged to cache invalidation
 * via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const favoritesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFavorites: build.query<string[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, async (client) =>
          (await client.fetchListings({ listName: "favorites" }))
            .map((fav) => fav.obj_id)
            // obj_id is NOT NULL server-side; the null check goes away once
            // skyportal-js models it as required (skyportal-js#6).
            .filter((objId): objId is string => objId != null),
        ),
      providesTags: ["Favorite"],
    }),
    addToFavorites: build.mutation<{ id: number }, string>({
      queryFn: (source_id, api) =>
        clientQuery(api, (client) =>
          client.postListing({ obj_id: source_id, list_name: "favorites" }),
        ),
      invalidatesTags: ["Favorite"],
    }),
    removeFromFavorites: build.mutation<void, string>({
      queryFn: (source_id, api) =>
        clientQuery(api, (client) =>
          client.deleteListingByName(source_id, "favorites"),
        ),
      invalidatesTags: ["Favorite"],
    }),
  }),
});

// Websocket-driven invalidation: refresh favorites on REFRESH_FAVORITES.
invalidateOnMessage("skyportal/REFRESH_FAVORITES", () => ["Favorite"]);

export const {
  useGetFavoritesQuery,
  useAddToFavoritesMutation,
  useRemoveFromFavoritesMutation,
} = favoritesApi;
