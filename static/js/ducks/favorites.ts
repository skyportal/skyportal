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
import { invalidateOnMessage } from "../api/wsInvalidation";

interface FavoriteListing {
  obj_id: string;
  [key: string]: unknown;
}

export const favoritesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFavorites: build.query<string[], void>({
      query: () => "api/listing?listName=favorites",
      transformResponse: (data: FavoriteListing[]) =>
        data?.map((fav) => fav.obj_id) ?? [],
      providesTags: ["Favorite"],
    }),
    addToFavorites: build.mutation<unknown, string>({
      query: (source_id) => ({
        url: "api/listing",
        method: "POST",
        body: {
          list_name: "favorites",
          obj_id: source_id,
        },
      }),
      invalidatesTags: ["Favorite"],
    }),
    removeFromFavorites: build.mutation<unknown, string>({
      query: (source_id) => ({
        url: "api/listing",
        method: "DELETE",
        body: {
          list_name: "favorites",
          obj_id: source_id,
        },
      }),
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
